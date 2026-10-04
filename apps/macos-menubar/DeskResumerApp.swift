import SwiftUI
import AppKit

// MARK: - Data Models
struct TargetChannel: Codable, Identifiable {
    var id: String { name }
    let name: String
    let running: Bool
    let busy: Bool
    let is_limited: Bool
    let wait_seconds: Int
    let desc: String?
}

struct PipelineTask: Codable, Identifiable {
    let id: Int
    let text: String
    var completed: Bool
}

struct PipelineQueue: Codable {
    let completed: Int
    let total: Int
    let tasks: [PipelineTask]
}

struct AppConfig: Codable {
    var monitoring: MonitoringConfig?
    var notifications: NotificationsConfig?
    var power: PowerConfig?
}

struct MonitoringConfig: Codable {
    var target_apps: String?
    var poll_interval_seconds: Int?
    var safety_buffer_seconds: Int?
}

struct PowerConfig: Codable {
    var prevent_sleep: Bool?
    var keep_display_on: Bool?
}


struct NotificationsConfig: Codable {
    var enabled: Bool?
    var ntfy: NtfyConfig?
    var discord: DiscordConfig?
    var telegram: TelegramConfig?
}

struct NtfyConfig: Codable {
    var topic: String?
}

struct DiscordConfig: Codable {
    var webhook_url: String?
}

struct TelegramConfig: Codable {
    var bot_token: String?
    var chat_id: String?
}

struct SupervisorState: Codable {
    let targets: [TargetChannel]
    let queue: PipelineQueue
    let config: AppConfig?
}

enum ActiveTab: String, CaseIterable {
    case dashboard = "Dashboard"
    case settings = "Integrations & Settings"
}

// MARK: - View Model
class SupervisorViewModel: ObservableObject {
    @Published var selectedTab: ActiveTab = .dashboard
    @Published var targets: [TargetChannel] = []
    @Published var tasks: [PipelineTask] = []
    @Published var completedCount: Int = 0
    @Published var totalCount: Int = 0
    @Published var isWatchdogRunning: Bool = false
    @Published var newTaskText: String = ""
    @Published var projectDir: String = "/Users/naqib/Documents/desk-resumer"

    // Settings fields
    @Published var telegramToken: String = ""
    @Published var telegramChatId: String = ""
    @Published var ntfyTopic: String = ""
    @Published var discordWebhook: String = ""
    @Published var targetApps: String = "all"
    @Published var safetyBuffer: Int = 120
    @Published var preventSleep: Bool = true
    @Published var saveStatusMessage: String? = nil

    private var timer: Timer?

    init() {
        // Read persisted project directory if saved, else default to current Documents/desk-resumer
        if let savedDir = UserDefaults.standard.string(forKey: "DeskResumerProjectDir"), FileManager.default.fileExists(atPath: savedDir) {
            self.projectDir = savedDir
        } else {
            let defaultPath = "/Users/naqib/Documents/desk-resumer"
            if FileManager.default.fileExists(atPath: defaultPath) {
                self.projectDir = defaultPath
            } else {
                self.projectDir = FileManager.default.currentDirectoryPath
            }
        }

        refreshState()

        // Background polling loop
        self.timer = Timer.scheduledTimer(withTimeInterval: 2.5, repeats: true) { [weak self] _ in
            self?.refreshState()
        }
    }

    func selectProjectFolder() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.directoryURL = URL(fileURLWithPath: projectDir)

        if panel.runModal() == .OK, let url = panel.url {
            self.projectDir = url.path
            UserDefaults.standard.set(url.path, forKey: "DeskResumerProjectDir")
            self.refreshState()
        }
    }

    func runCli(_ args: [String]) -> String? {
        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = ["-m", "desk_resumer.cli"] + args
        process.currentDirectoryURL = URL(fileURLWithPath: projectDir)
        process.standardOutput = pipe
        process.standardError = FileHandle.nullDevice

        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            return String(data: data, encoding: .utf8)
        } catch {
            return nil
        }
    }

    func refreshState() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self, let output = self.runCli(["status-json"]) else { return }
            guard let data = output.data(using: .utf8) else { return }

            do {
                let state = try JSONDecoder().decode(SupervisorState.self, from: data)
                DispatchQueue.main.async {
                    self.targets = state.targets
                    self.tasks = state.queue.tasks
                    self.completedCount = state.queue.completed
                    self.totalCount = state.queue.total

                    // Populate settings from config if not dirty
                    if let cfg = state.config {
                        if self.ntfyTopic.isEmpty { self.ntfyTopic = cfg.notifications?.ntfy?.topic ?? "" }
                        if self.telegramToken.isEmpty { self.telegramToken = cfg.notifications?.telegram?.bot_token ?? "" }
                        if self.telegramChatId.isEmpty { self.telegramChatId = cfg.notifications?.telegram?.chat_id ?? "" }
                        if self.discordWebhook.isEmpty { self.discordWebhook = cfg.notifications?.discord?.webhook_url ?? "" }
                        if let buf = cfg.monitoring?.safety_buffer_seconds { self.safetyBuffer = buf }
                        if let tg = cfg.monitoring?.target_apps { self.targetApps = tg }
                    }
                }
            } catch {
                // Ignore decoding error
            }
        }
    }

    func toggleWatchdog() {
        isWatchdogRunning.toggle()
        let action = isWatchdogRunning ? "start" : "stop"
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["service", action])
            self?.refreshState()
        }
    }

    func toggleTask(_ task: PipelineTask) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["toggle-task", "\(task.id)"])
            self?.refreshState()
        }
    }

    func addTask() {
        let text = newTaskText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        newTaskText = ""
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["add-task", text])
            self?.refreshState()
        }
    }

    func triggerPrompt(target: String) {
        let key = target.lowercased().contains("chatgpt") ? "chatgpt" : "antigravity"
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["test-resume", "--app", key, "--prompt", "Testing DeskResumer trigger."])
            self?.refreshState()
        }
    }

    func testPhoneAlert() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["test-notify", "--message", "⚡ Test alert from macOS Native Menu Bar!"])
        }
    }

    func saveSettings() {
        var cfg = AppConfig()
        cfg.monitoring = MonitoringConfig(
            target_apps: targetApps,
            poll_interval_seconds: 30,
            safety_buffer_seconds: safetyBuffer
        )
        cfg.power = PowerConfig()
        cfg.notifications = NotificationsConfig(
            enabled: true,
            ntfy: NtfyConfig(topic: ntfyTopic),
            discord: DiscordConfig(webhook_url: discordWebhook),
            telegram: TelegramConfig(bot_token: telegramToken, chat_id: telegramChatId)
        )

        do {
            let data = try JSONEncoder().encode(cfg)
            if let jsonString = String(data: data, encoding: .utf8) {
                DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                    _ = self?.runCli(["save-config-json", jsonString])
                    DispatchQueue.main.async {
                        self?.saveStatusMessage = "Settings saved successfully!"
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            self?.saveStatusMessage = nil
                        }
                    }
                }
            }
        } catch {
            saveStatusMessage = "Failed to encode settings."
        }
    }
}

// MARK: - Main Popover View
struct PopoverContentView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Header Bar
            HStack {
                HStack(spacing: 8) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(model.isWatchdogRunning ? .green : .secondary)

                    VStack(alignment: .leading, spacing: 1) {
                        Text("DeskResumer")
                            .font(.system(size: 13, weight: .semibold))
                        Text("AUTONOMOUS SUPERVISOR")
                            .font(.system(size: 9, weight: .medium, design: .monospaced))
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                Button(action: { model.toggleWatchdog() }) {
                    Text(model.isWatchdogRunning ? "Stop" : "Start")
                        .font(.system(size: 11, weight: .semibold))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(model.isWatchdogRunning ? Color.red.opacity(0.15) : Color.primary.opacity(0.1))
                        .foregroundColor(model.isWatchdogRunning ? .red : .primary)
                        .cornerRadius(6)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(NSColor.windowBackgroundColor))

            // Navigation Segmented Control
            Picker("", selection: $model.selectedTab) {
                Text("Dashboard").tag(ActiveTab.dashboard)
                Text("Integrations & Settings").tag(ActiveTab.settings)
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(Color(NSColor.windowBackgroundColor))

            Divider()

            // Viewport Switcher
            if model.selectedTab == .dashboard {
                DashboardView(model: model)
            } else {
                SettingsView(model: model)
            }

            Divider()

            // Footer Bar
            HStack {
                Button(action: { model.testPhoneAlert() }) {
                    Label("Test Push Alert", systemImage: "bell.badge")
                        .font(.system(size: 11))
                }
                .buttonStyle(.plain)
                .foregroundColor(.secondary)

                Spacer()

                Button(action: { NSApplication.shared.terminate(nil) }) {
                    Text("Quit")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(Color(NSColor.windowBackgroundColor))
        }
        .frame(width: 380, height: 530)
    }
}

// MARK: - Tab 1: Dashboard View
struct DashboardView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                // Workspace Path Card
                HStack(spacing: 6) {
                    Image(systemName: "folder.fill")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                    Text(URL(fileURLWithPath: model.projectDir).lastPathComponent)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                    Spacer()
                    Button("Change...") { model.selectProjectFolder() }
                        .font(.system(size: 10))
                        .buttonStyle(.bordered)
                        .controlSize(.mini)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(RoundedRectangle(cornerRadius: 6).fill(Color(NSColor.controlBackgroundColor)))

                // Channel Cards
                VStack(spacing: 6) {
                    ForEach(model.targets) { target in
                        ChannelRowView(target: target, onTrigger: {
                            model.triggerPrompt(target: target.name)
                        })
                    }
                }

                // Execution Pipeline
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("EXECUTION PIPELINE")
                            .font(.system(size: 10, weight: .semibold, design: .monospaced))
                            .foregroundColor(.secondary)
                        Spacer()
                        Text("\(model.completedCount) / \(model.totalCount) (\(model.totalCount > 0 ? Int(Double(model.completedCount)/Double(model.totalCount)*100) : 0)%)")
                            .font(.system(size: 10, weight: .medium, design: .monospaced))
                            .foregroundColor(.secondary)
                    }

                    ProgressView(value: Double(model.completedCount), total: Double(max(1, model.totalCount)))
                        .progressViewStyle(.linear)
                        .tint(.white)

                    VStack(spacing: 4) {
                        ForEach(model.tasks) { task in
                            HStack(spacing: 8) {
                                Button(action: { model.toggleTask(task) }) {
                                    Image(systemName: task.completed ? "checkmark.square.fill" : "square")
                                        .font(.system(size: 13))
                                        .foregroundColor(task.completed ? .secondary : .primary)
                                }
                                .buttonStyle(.plain)

                                Text(task.text)
                                    .font(.system(size: 11))
                                    .strikethrough(task.completed)
                                    .foregroundColor(task.completed ? .secondary : .primary)
                                    .lineLimit(2)

                                Spacer()
                            }
                            .padding(.vertical, 2)
                        }
                    }

                    // Add Task Field
                    HStack {
                        TextField("Append subtask...", text: $model.newTaskText)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 11))
                            .onSubmit { model.addTask() }

                        Button(action: { model.addTask() }) {
                            Image(systemName: "plus")
                                .font(.system(size: 11, weight: .semibold))
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    .padding(.top, 4)
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color(NSColor.controlBackgroundColor)))
            }
            .padding(14)
        }
    }
}

// MARK: - Tab 2: Settings & Integrations View
struct SettingsView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                // Telegram Section
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Label("Telegram Two-Way Bot", systemImage: "paperplane.fill")
                            .font(.system(size: 11, weight: .semibold))
                        Spacer()
                        Text(!model.telegramToken.isEmpty ? "Connected" : "Not Set")
                            .font(.system(size: 9, weight: .semibold, design: .monospaced))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(!model.telegramToken.isEmpty ? Color.green.opacity(0.15) : Color.secondary.opacity(0.15))
                            .foregroundColor(!model.telegramToken.isEmpty ? .green : .secondary)
                            .cornerRadius(4)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text("BOT TOKEN").font(.system(size: 9, weight: .medium, design: .monospaced)).foregroundColor(.secondary)
                        SecureField("123456:ABC-DEF...", text: $model.telegramToken)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 11))
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text("ALLOWED CHAT ID").font(.system(size: 9, weight: .medium, design: .monospaced)).foregroundColor(.secondary)
                        TextField("e.g. 987654321", text: $model.telegramChatId)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 11))
                    }

                    Text("Text /status, /skip, /pause, /resume from your phone.")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color(NSColor.controlBackgroundColor)))

                // Mobile Alerts (ntfy)
                VStack(alignment: .leading, spacing: 8) {
                    Label("ntfy.sh Mobile Push Alerts", systemImage: "bell.fill")
                        .font(.system(size: 11, weight: .semibold))

                    VStack(alignment: .leading, spacing: 2) {
                        Text("TOPIC NAME").font(.system(size: 9, weight: .medium, design: .monospaced)).foregroundColor(.secondary)
                        TextField("desk-resumer-naqib", text: $model.ntfyTopic)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 11))
                    }
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color(NSColor.controlBackgroundColor)))

                // Cooldown Rules
                VStack(alignment: .leading, spacing: 8) {
                    Label("Automation & Quota Rules", systemImage: "slider.horizontal.3")
                        .font(.system(size: 11, weight: .semibold))

                    HStack {
                        Text("Safety Buffer: \(model.safetyBuffer)s")
                            .font(.system(size: 11))
                        Spacer()
                        Stepper("", value: $model.safetyBuffer, in: 30...600, step: 30)
                            .controlSize(.mini)
                    }

                    Picker("Monitored Targets", selection: $model.targetApps) {
                        Text("All (ChatGPT & Antigravity)").tag("all")
                        Text("ChatGPT Only").tag("chatgpt")
                        Text("Antigravity Only").tag("antigravity")
                    }
                    .font(.system(size: 11))
                }
                .padding(12)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color(NSColor.controlBackgroundColor)))

                // Save Button & Confirmation
                VStack(spacing: 6) {
                    Button(action: { model.saveSettings() }) {
                        HStack {
                            Spacer()
                            Text("Save Configuration")
                                .font(.system(size: 12, weight: .semibold))
                            Spacer()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.white)
                    .foregroundColor(.black)

                    if let msg = model.saveStatusMessage {
                        Text(msg)
                            .font(.system(size: 11))
                            .foregroundColor(.green)
                    }
                }
            }
            .padding(14)
        }
    }
}

// MARK: - Channel Row Component
struct ChannelRowView: View {
    let target: TargetChannel
    let onTrigger: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 10) {
            Image(systemName: target.name.lowercased().contains("chatgpt") ? "sparkles" : "terminal.fill")
                .font(.system(size: 13))
                .foregroundColor(.secondary)

            VStack(alignment: .leading, spacing: 2) {
                Text(target.name)
                    .font(.system(size: 12, weight: .medium))

                if !target.running {
                    Text("Offline")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                } else if target.is_limited {
                    Text("Cooldown: \(target.wait_seconds / 60)m left")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.orange)
                } else if target.busy {
                    Text("Actively Generating")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(.green)
                } else {
                    Text("Ready (Idle)")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            Button(action: onTrigger) {
                Text("Trigger")
                    .font(.system(size: 10, weight: .medium))
            }
            .buttonStyle(.bordered)
            .controlSize(.mini)
        }
        .padding(10)
        .background(RoundedRectangle(cornerRadius: 8).fill(Color(NSColor.controlBackgroundColor)))
    }
}

// MARK: - Entry Point
@main
struct DeskResumerApp: App {
    @StateObject private var model = SupervisorViewModel()

    var body: some Scene {
        MenuBarExtra {
            PopoverContentView(model: model)
        } label: {
            let isLimited = model.targets.contains { $0.is_limited }
            let iconName = isLimited ? "hourglass.bottomhalf.filled" : (model.isWatchdogRunning ? "bolt.fill" : "bolt")
            Image(systemName: iconName)
        }
        .menuBarExtraStyle(.window)
    }
}
