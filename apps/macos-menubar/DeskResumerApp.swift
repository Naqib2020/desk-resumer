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
    case settings = "Settings"
}

// MARK: - View Model
class SupervisorViewModel: ObservableObject {
    @Published var selectedTab: ActiveTab = .dashboard
    @Published var targets: [TargetChannel] = [
        TargetChannel(name: "ChatGPT", running: false, busy: false, is_limited: false, wait_seconds: 0, desc: nil),
        TargetChannel(name: "Antigravity", running: false, busy: false, is_limited: false, wait_seconds: 0, desc: nil)
    ]
    @Published var tasks: [PipelineTask] = []
    @Published var completedCount: Int = 0
    @Published var totalCount: Int = 0
    @Published var isWatchdogRunning: Bool = false
    @Published var newTaskText: String = ""
    @Published var projectDir: String = FileManager.default.currentDirectoryPath

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
        if let savedDir = UserDefaults.standard.string(forKey: "DeskResumerProjectDir"), FileManager.default.fileExists(atPath: savedDir) {
            self.projectDir = savedDir
        } else {
            // Dynamically locate repository root if bundled inside apps/macos-menubar
            let bundleUrl = Bundle.main.bundleURL
            let candidateDir = bundleUrl.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().path
            let pyprojectCandidate = (candidateDir as NSString).appendingPathComponent("pyproject.toml")
            if FileManager.default.fileExists(atPath: pyprojectCandidate) {
                self.projectDir = candidateDir
            } else if FileManager.default.fileExists(atPath: (FileManager.default.currentDirectoryPath as NSString).appendingPathComponent("pyproject.toml")) {
                self.projectDir = FileManager.default.currentDirectoryPath
            } else {
                self.projectDir = FileManager.default.currentDirectoryPath
            }
        }

        refreshState()

        // Only prompt for Accessibility if not already trusted by macOS
        if !AXIsProcessTrusted() {
            let axOptions = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
            _ = AXIsProcessTrustedWithOptions(axOptions)
        }

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

    private var repoDir: String {
        let bundleUrl = Bundle.main.bundleURL
        let candidateDir = bundleUrl.deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().path
        let pyprojectCandidate = (candidateDir as NSString).appendingPathComponent("pyproject.toml")
        if FileManager.default.fileExists(atPath: pyprojectCandidate) {
            return candidateDir
        }
        return "/Users/naqib/Documents/desk-resumer"
    }

    func runCli(_ args: [String]) -> String? {
        let process = Process()
        let pipe = Pipe()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
        process.arguments = ["-m", "desk_resumer.cli"] + args
        process.currentDirectoryURL = URL(fileURLWithPath: projectDir)

        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = repoDir
        process.environment = env

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

    func clearCompletedTasks() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["clear-completed"])
            self?.refreshState()
        }
    }

    func triggerPrompt(target: String) {
        let isChatGPT = target.lowercased().contains("chatgpt")
        let promptToSend = tasks.first(where: { !$0.completed })?.text ?? "Continue"

        if !AXIsProcessTrusted() {
            let axOptions = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
            _ = AXIsProcessTrustedWithOptions(axOptions)
            return
        }

        // Native instant activation & keystroke injection in Swift
        injectNativePrompt(isChatGPT: isChatGPT, prompt: promptToSend)
    }

    private func injectNativePrompt(isChatGPT: Bool, prompt: String) {
        let appName = isChatGPT ? "ChatGPT" : "Antigravity"
        let bundleIds = isChatGPT ? ["com.openai.codex", "com.openai.chat"] : ["com.google.antigravity", "com.google.antigravity-ide"]

        let apps = NSWorkspace.shared.runningApplications
        guard let app = apps.first(where: { runningApp in
            if let bid = runningApp.bundleIdentifier, bundleIds.contains(bid) { return true }
            if let name = runningApp.localizedName, name.lowercased().contains(appName.lowercased()) { return true }
            return false
        }) else {
            // Fallback to CLI test-resume if process not found in GUI workspace
            let key = isChatGPT ? "chatgpt" : "antigravity"
            DispatchQueue.global(qos: .userInitiated).async { [weak self] in
                _ = self?.runCli(["test-resume", "--app", key, "--prompt", prompt])
                self?.refreshState()
            }
            return
        }

        // 1. Activate target application
        app.activate()

        // 2. Put prompt into General Clipboard
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(prompt, forType: .string)

        // 3. Post Cmd+V and Return via native CGEvent
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            let src = CGEventSource(stateID: .hidSystemState)

            // Cmd + V (virtualKey: 9)
            if let vDown = CGEvent(keyboardEventSource: src, virtualKey: 9, keyDown: true) {
                vDown.flags = .maskCommand
                vDown.post(tap: .cghidEventTap)
            }
            if let vUp = CGEvent(keyboardEventSource: src, virtualKey: 9, keyDown: false) {
                vUp.flags = .maskCommand
                vUp.post(tap: .cghidEventTap)
            }

            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { [weak self] in
                // Return (virtualKey: 36)
                if let retDown = CGEvent(keyboardEventSource: src, virtualKey: 36, keyDown: true) {
                    retDown.post(tap: .cghidEventTap)
                }
                if let retUp = CGEvent(keyboardEventSource: src, virtualKey: 36, keyDown: false) {
                    retUp.post(tap: .cghidEventTap)
                }

                self?.refreshState()
            }
        }
    }

    func testPhoneAlert() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["test-notify", "--message", "⚡ Alert from DeskResumer Liquid Glass UI!"])
        }
    }

    func saveSettings() {
        var cfg = AppConfig()
        cfg.monitoring = MonitoringConfig(
            target_apps: targetApps,
            poll_interval_seconds: 30,
            safety_buffer_seconds: safetyBuffer
        )
        cfg.power = PowerConfig(prevent_sleep: true, keep_display_on: false)
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
                        self?.saveStatusMessage = "Saved to config.yaml"
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            self?.saveStatusMessage = nil
                        }
                    }
                }
            }
        } catch {
            saveStatusMessage = "Encoding error."
        }
    }
}

// MARK: - Liquid Glass View Modifiers & Styles
struct LiquidGlassCardModifier: ViewModifier {
    var cornerRadius: CGFloat = 12

    func body(content: Content) -> some View {
        content
            .background(
                ZStack {
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .fill(.ultraThinMaterial)
                    
                    RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                        .fill(Color(nsColor: .controlBackgroundColor).opacity(0.35))
                }
            )
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
                    .strokeBorder(
                        LinearGradient(
                            stops: [
                                .init(color: Color.white.opacity(0.55), location: 0.0),
                                .init(color: Color.white.opacity(0.12), location: 0.4),
                                .init(color: Color.white.opacity(0.04), location: 1.0)
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        lineWidth: 0.75
                    )
            )
            .shadow(color: Color.black.opacity(0.05), radius: 8, x: 0, y: 4)
    }
}

extension View {
    func liquidGlassCard(cornerRadius: CGFloat = 12) -> some View {
        self.modifier(LiquidGlassCardModifier(cornerRadius: cornerRadius))
    }
}

// MARK: - Popover Content View
struct PopoverContentView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        ZStack {
            // Ambient Liquid Glass Gradient Backdrop
            LinearGradient(
                colors: [
                    Color(nsColor: .windowBackgroundColor).opacity(0.85),
                    Color(nsColor: .controlBackgroundColor).opacity(0.7)
                ],
                startPoint: .top,
                endPoint: .bottom
            )
            .background(.ultraThinMaterial)
            .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header Glass Bar
                HStack(spacing: 10) {
                    // Logo Badge
                    ZStack {
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .fill(
                                LinearGradient(
                                    colors: model.isWatchdogRunning ? [Color.green, Color.mint] : [Color.blue, Color.cyan],
                                    startPoint: .topLeading,
                                    endPoint: .bottomTrailing
                                )
                            )
                            .frame(width: 28, height: 28)
                            .shadow(color: (model.isWatchdogRunning ? Color.green : Color.blue).opacity(0.35), radius: 6, y: 2)

                        Image(systemName: "bolt.fill")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundColor(.white)
                    }

                    VStack(alignment: .leading, spacing: 1) {
                        Text("DeskResumer")
                            .font(.system(size: 13, weight: .bold, design: .rounded))
                            .foregroundColor(.primary)
                        
                        Text("AUTONOMOUS SUPERVISOR")
                            .font(.system(size: 8, weight: .semibold, design: .monospaced))
                            .foregroundColor(.secondary)
                            .tracking(0.6)
                    }

                    Spacer()

                    // Start/Stop Glass Pill Button
                    Button(action: {
                        withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                            model.toggleWatchdog()
                        }
                    }) {
                        HStack(spacing: 5) {
                            Circle()
                                .fill(model.isWatchdogRunning ? Color.green : Color.secondary)
                                .frame(width: 6, height: 6)
                                .shadow(color: model.isWatchdogRunning ? Color.green.opacity(0.8) : Color.clear, radius: 4)

                            Text(model.isWatchdogRunning ? "Active" : "Idle")
                                .font(.system(size: 11, weight: .semibold, design: .rounded))
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(
                            Capsule()
                                .fill(model.isWatchdogRunning ? Color.green.opacity(0.15) : Color(nsColor: .controlBackgroundColor).opacity(0.6))
                        )
                        .overlay(
                            Capsule()
                                .strokeBorder(model.isWatchdogRunning ? Color.green.opacity(0.4) : Color.white.opacity(0.3), lineWidth: 0.75)
                        )
                        .contentShape(Capsule())
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 16)
                .padding(.top, 14)
                .padding(.bottom, 10)

                // Liquid Segmented Pill Switcher
                HStack(spacing: 3) {
                    ForEach(ActiveTab.allCases, id: \.self) { tab in
                        Button(action: {
                            withAnimation(.spring(response: 0.28, dampingFraction: 0.78)) {
                                model.selectedTab = tab
                            }
                        }) {
                            Text(tab.rawValue)
                                .font(.system(size: 11, weight: model.selectedTab == tab ? .semibold : .medium, design: .rounded))
                                .foregroundColor(model.selectedTab == tab ? .primary : .secondary)
                                .padding(.vertical, 6)
                                .frame(maxWidth: .infinity)
                                .background(
                                    ZStack {
                                        if model.selectedTab == tab {
                                            RoundedRectangle(cornerRadius: 7, style: .continuous)
                                                .fill(Color(nsColor: .controlBackgroundColor).opacity(0.9))
                                                .overlay(
                                                    RoundedRectangle(cornerRadius: 7, style: .continuous)
                                                        .strokeBorder(Color.white.opacity(0.5), lineWidth: 0.5)
                                                )
                                                .shadow(color: Color.black.opacity(0.06), radius: 4, y: 1.5)
                                        } else {
                                            Color.black.opacity(0.001)
                                        }
                                    }
                                )
                                .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(3)
                .background(
                    RoundedRectangle(cornerRadius: 9, style: .continuous)
                        .fill(Color.black.opacity(0.06))
                        .overlay(
                            RoundedRectangle(cornerRadius: 9, style: .continuous)
                                .strokeBorder(Color.white.opacity(0.2), lineWidth: 0.5)
                        )
                )
                .padding(.horizontal, 16)
                .padding(.bottom, 10)

                Divider()
                    .opacity(0.5)

                // Tab Content
                if model.selectedTab == .dashboard {
                    LiquidDashboardView(model: model)
                } else {
                    LiquidSettingsView(model: model)
                }

                Divider()
                    .opacity(0.5)

                // Footer Bar
                HStack {
                    Button(action: { model.testPhoneAlert() }) {
                        HStack(spacing: 5) {
                            Image(systemName: "bell.badge.fill")
                                .font(.system(size: 10))
                                .foregroundColor(.blue)
                            Text("Test Push Alert")
                                .font(.system(size: 11, weight: .medium, design: .rounded))
                        }
                        .padding(.vertical, 4)
                        .padding(.horizontal, 6)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .foregroundColor(.secondary)

                    Spacer()

                    Button(action: { NSApplication.shared.terminate(nil) }) {
                        Text("Quit")
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundColor(.secondary)
                            .padding(.vertical, 4)
                            .padding(.horizontal, 6)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
            }
        }
        .frame(width: 370, height: 520)
    }
}

// MARK: - Liquid Dashboard View
struct LiquidDashboardView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 12) {
                
                // Workspace Glass Capsule
                HStack(spacing: 8) {
                    Image(systemName: "folder.fill")
                        .font(.system(size: 11))
                        .foregroundColor(.blue)
                    
                    Text(URL(fileURLWithPath: model.projectDir).lastPathComponent)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                    
                    Spacer()
                    
                    Button("Change...") { model.selectProjectFolder() }
                        .font(.system(size: 10, weight: .medium, design: .rounded))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(Capsule().fill(Color.white.opacity(0.4)))
                        .overlay(Capsule().strokeBorder(Color.white.opacity(0.6), lineWidth: 0.5))
                        .contentShape(Capsule())
                        .buttonStyle(.plain)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .liquidGlassCard(cornerRadius: 10)

                // Channels Section (ChatGPT & Antigravity)
                VStack(spacing: 8) {
                    ForEach(model.targets) { target in
                        LiquidChannelCard(target: target, onTrigger: {
                            model.triggerPrompt(target: target.name)
                        })
                    }
                }

                // Execution Pipeline Glass Box
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        HStack(spacing: 6) {
                            Image(systemName: "checklist")
                                .font(.system(size: 11))
                                .foregroundColor(.indigo)
                            Text("EXECUTION PIPELINE")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundColor(.secondary)
                                .tracking(0.5)
                        }
                        
                        Spacer()

                        if model.completedCount > 0 {
                            Button(action: {
                                withAnimation(.spring(response: 0.25, dampingFraction: 0.7)) {
                                    model.clearCompletedTasks()
                                }
                            }) {
                                Text("Clear Done")
                                    .font(.system(size: 9, weight: .semibold, design: .rounded))
                                    .foregroundColor(.secondary)
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Capsule().fill(Color.black.opacity(0.06)))
                                    .overlay(Capsule().strokeBorder(Color.white.opacity(0.3), lineWidth: 0.5))
                                    .contentShape(Capsule())
                            }
                            .buttonStyle(.plain)
                        }

                        Text("\(model.completedCount)/\(model.totalCount) (\(model.totalCount > 0 ? Int(Double(model.completedCount)/Double(model.totalCount)*100) : 0)%)")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Capsule().fill(Color.blue.opacity(0.12)))
                            .foregroundColor(.blue)
                    }

                    // Liquid Progress Track
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule()
                                .fill(Color.black.opacity(0.08))
                                .frame(height: 5)

                            Capsule()
                                .fill(
                                    LinearGradient(
                                        colors: [Color.blue, Color.cyan],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .frame(width: max(0, min(geo.size.width, geo.size.width * CGFloat(Double(model.completedCount) / Double(max(1, model.totalCount))))), height: 5)
                                .shadow(color: Color.blue.opacity(0.3), radius: 3)
                        }
                    }
                    .frame(height: 5)

                    // Task Checklist Items
                    if model.tasks.isEmpty {
                        VStack(spacing: 5) {
                            Image(systemName: "list.clipboard")
                                .font(.system(size: 18))
                                .foregroundColor(.secondary.opacity(0.5))
                                .padding(.top, 4)

                            Text("No Subtasks Queued")
                                .font(.system(size: 11, weight: .semibold, design: .rounded))
                                .foregroundColor(.primary)

                            Text("Tasks added below or in TASKS.md execute in sequence. Without tasks, DeskResumer injects the default resume prompt.")
                                .font(.system(size: 9.5, design: .rounded))
                                .foregroundColor(.secondary)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal, 12)
                                .padding(.bottom, 4)
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .fill(Color.black.opacity(0.025))
                        )
                    } else {
                        VStack(spacing: 6) {
                            ForEach(model.tasks) { task in
                                Button(action: {
                                    withAnimation(.spring(response: 0.25, dampingFraction: 0.7)) {
                                        model.toggleTask(task)
                                    }
                                }) {
                                    HStack(spacing: 8) {
                                        ZStack {
                                            RoundedRectangle(cornerRadius: 4, style: .continuous)
                                                .fill(task.completed ? Color.green : Color.black.opacity(0.08))
                                                .frame(width: 16, height: 16)
                                                .overlay(
                                                    RoundedRectangle(cornerRadius: 4, style: .continuous)
                                                        .strokeBorder(task.completed ? Color.green : Color.white.opacity(0.4), lineWidth: 0.75)
                                                )

                                            if task.completed {
                                                Image(systemName: "checkmark")
                                                    .font(.system(size: 9, weight: .bold))
                                                    .foregroundColor(.white)
                                            }
                                        }

                                        Text(task.text)
                                            .font(.system(size: 11, weight: .medium, design: .rounded))
                                            .strikethrough(task.completed)
                                            .foregroundColor(task.completed ? .secondary : .primary)
                                            .lineLimit(2)

                                        Spacer()
                                    }
                                    .padding(.vertical, 3)
                                    .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    }

                    // Add Subtask Input
                    HStack(spacing: 6) {
                        TextField("Append subtask to queue...", text: $model.newTaskText)
                            .textFieldStyle(.plain)
                            .font(.system(size: 11, design: .rounded))
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(
                                RoundedRectangle(cornerRadius: 8, style: .continuous)
                                    .fill(Color(nsColor: .controlBackgroundColor).opacity(0.5))
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 8, style: .continuous)
                                    .strokeBorder(Color.white.opacity(0.4), lineWidth: 0.75)
                            )
                            .onSubmit { model.addTask() }

                        Button(action: { model.addTask() }) {
                            Image(systemName: "plus")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.white)
                                .frame(width: 26, height: 26)
                                .background(Circle().fill(Color.blue))
                                .shadow(color: Color.blue.opacity(0.35), radius: 4)
                                .contentShape(Circle())
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.top, 4)
                }
                .padding(12)
                .liquidGlassCard(cornerRadius: 12)
            }
            .padding(14)
        }
    }
}

// MARK: - Liquid Channel Card
struct LiquidChannelCard: View {
    let target: TargetChannel
    let onTrigger: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Channel Icon with Ambient Shadow
            ZStack {
                RoundedRectangle(cornerRadius: 9, style: .continuous)
                    .fill(
                        LinearGradient(
                            colors: target.name.lowercased().contains("chatgpt") ? [Color.green.opacity(0.2), Color.mint.opacity(0.1)] : [Color.indigo.opacity(0.2), Color.purple.opacity(0.1)],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 34, height: 34)
                    .overlay(
                        RoundedRectangle(cornerRadius: 9, style: .continuous)
                            .strokeBorder(Color.white.opacity(0.4), lineWidth: 0.5)
                    )

                Image(systemName: target.name.lowercased().contains("chatgpt") ? "sparkles" : "terminal.fill")
                    .font(.system(size: 14))
                    .foregroundColor(target.name.lowercased().contains("chatgpt") ? .green : .indigo)
            }

            // Info
            VStack(alignment: .leading, spacing: 2) {
                Text(target.name)
                    .font(.system(size: 12, weight: .bold, design: .rounded))

                if !target.running {
                    Text("Offline")
                        .font(.system(size: 10, weight: .medium, design: .rounded))
                        .foregroundColor(.secondary)
                } else if target.is_limited {
                    Text("Cooldown: \(target.wait_seconds / 60)m left")
                        .font(.system(size: 10, weight: .semibold, design: .rounded))
                        .foregroundColor(.orange)
                } else if target.busy {
                    Text("Actively Generating")
                        .font(.system(size: 10, weight: .semibold, design: .rounded))
                        .foregroundColor(.green)
                } else {
                    Text("Ready (Idle)")
                        .font(.system(size: 10, weight: .medium, design: .rounded))
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            // Trigger Button with Specular Gloss
            Button(action: onTrigger) {
                Text("Trigger")
                    .font(.system(size: 10, weight: .semibold, design: .rounded))
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        Capsule()
                            .fill(Color(nsColor: .controlBackgroundColor).opacity(0.75))
                    )
                    .overlay(
                        Capsule()
                            .strokeBorder(Color.white.opacity(0.6), lineWidth: 0.75)
                    )
                    .shadow(color: Color.black.opacity(0.04), radius: 3, y: 1)
                    .contentShape(Capsule())
            }
            .buttonStyle(.plain)
        }
        .padding(10)
        .liquidGlassCard(cornerRadius: 12)
    }
}

// MARK: - Liquid Settings View
struct LiquidSettingsView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        ScrollView(showsIndicators: false) {
            VStack(spacing: 12) {
                // Telegram Glass Group
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        HStack(spacing: 6) {
                            Image(systemName: "paperplane.fill")
                                .font(.system(size: 11))
                                .foregroundColor(.blue)
                            Text("TELEGRAM REMOTE BOT")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .foregroundColor(.secondary)
                                .tracking(0.5)
                        }
                        
                        Spacer()
                        
                        HStack(spacing: 4) {
                            Circle()
                                .fill(!model.telegramToken.isEmpty ? Color.green : Color.secondary)
                                .frame(width: 5, height: 5)
                            Text(!model.telegramToken.isEmpty ? "Connected" : "Not Configured")
                                .font(.system(size: 9, weight: .semibold, design: .monospaced))
                                .foregroundColor(!model.telegramToken.isEmpty ? .green : .secondary)
                        }
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(!model.telegramToken.isEmpty ? Color.green.opacity(0.12) : Color.secondary.opacity(0.12)))
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        Text("BOT TOKEN").font(.system(size: 8, weight: .semibold, design: .monospaced)).foregroundColor(.secondary)
                        SecureField("123456:ABC-DEF...", text: $model.telegramToken)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 11))
                    }

                    VStack(alignment: .leading, spacing: 3) {
                        Text("ALLOWED CHAT ID").font(.system(size: 8, weight: .semibold, design: .monospaced)).foregroundColor(.secondary)
                        TextField("e.g. 987654321", text: $model.telegramChatId)
                            .textFieldStyle(.roundedBorder)
                            .font(.system(size: 11))
                    }

                    Text("Text /status, /skip, /pause, /resume from your phone.")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
                .padding(12)
                .liquidGlassCard(cornerRadius: 12)

                // Mobile Alerts Glass Group
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 6) {
                        Image(systemName: "bell.fill")
                            .font(.system(size: 11))
                            .foregroundColor(.orange)
                        Text("NTFY.SH MOBILE PUSH TOPIC")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundColor(.secondary)
                            .tracking(0.5)
                    }

                    TextField("e.g. my-desk-alerts", text: $model.ntfyTopic)
                        .textFieldStyle(.roundedBorder)
                        .font(.system(size: 11))
                }
                .padding(12)
                .liquidGlassCard(cornerRadius: 12)

                // Cooldown Rules Glass Group
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 6) {
                        Image(systemName: "slider.horizontal.3")
                            .font(.system(size: 11))
                            .foregroundColor(.cyan)
                        Text("AUTOMATION RULES")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                            .foregroundColor(.secondary)
                            .tracking(0.5)
                    }

                    HStack {
                        Text("Safety Buffer: \(model.safetyBuffer)s")
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                        Spacer()
                        Stepper("", value: $model.safetyBuffer, in: 30...600, step: 30)
                            .controlSize(.mini)
                    }

                    Picker("Monitored Targets", selection: $model.targetApps) {
                        Text("All (ChatGPT & Antigravity)").tag("all")
                        Text("ChatGPT Only").tag("chatgpt")
                        Text("Antigravity Only").tag("antigravity")
                    }
                    .font(.system(size: 11, design: .rounded))
                }
                .padding(12)
                .liquidGlassCard(cornerRadius: 12)

                // Save Glass Button
                VStack(spacing: 6) {
                    Button(action: { model.saveSettings() }) {
                        HStack {
                            Spacer()
                            Text("Save Configuration")
                                .font(.system(size: 12, weight: .bold, design: .rounded))
                                .foregroundColor(.white)
                            Spacer()
                        }
                        .padding(.vertical, 8)
                        .background(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .fill(
                                    LinearGradient(
                                        colors: [Color.blue, Color.cyan],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .shadow(color: Color.blue.opacity(0.3), radius: 6, y: 2)
                        )
                        .contentShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
                    }
                    .buttonStyle(.plain)

                    if let msg = model.saveStatusMessage {
                        Text(msg)
                            .font(.system(size: 10, weight: .semibold, design: .monospaced))
                            .foregroundColor(.green)
                    }
                }
                .padding(.top, 4)
            }
            .padding(14)
        }
    }
}

// MARK: - Main Application
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
