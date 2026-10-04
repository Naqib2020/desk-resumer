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

struct SupervisorState: Codable {
    let targets: [TargetChannel]
    let queue: PipelineQueue
}

// MARK: - View Model
class SupervisorViewModel: ObservableObject {
    @Published var targets: [TargetChannel] = []
    @Published var tasks: [PipelineTask] = []
    @Published var completedCount: Int = 0
    @Published var totalCount: Int = 0
    @Published var isWatchdogRunning: Bool = false
    @Published var newTaskText: String = ""

    private var timer: Timer?
    let projectDir: String

    init() {
        // Resolve project directory from binary location or standard path
        self.projectDir = FileManager.default.currentDirectoryPath
        refreshState()
        
        // Polling timer every 2.5 seconds
        self.timer = Timer.scheduledTimer(withTimeInterval: 2.5, repeats: true) { [weak self] _ in
            self?.refreshState()
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
                }
            } catch {
                // Ignore parse errors on partial writes
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
            _ = self?.runCli(["test-resume", "--app", key, "--prompt", "Testing DeskResumer Native MenuBar trigger."])
            self?.refreshState()
        }
    }

    func testPhoneAlert() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            _ = self?.runCli(["test-notify", "--message", "⚡ Test alert from macOS Native Menu Bar!"])
        }
    }
}

// MARK: - SwiftUI Menu Bar Popover View
struct PopoverContentView: View {
    @ObservedObject var model: SupervisorViewModel

    var body: some View {
        VStack(spacing: 0) {
            // Header
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
            
            Divider()

            // Main Content Area
            ScrollView {
                VStack(spacing: 14) {
                    
                    // Channels Section
                    VStack(spacing: 8) {
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

                        // Tasks List
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
                                .padding(.vertical, 3)
                            }
                        }

                        // Add Task Input
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

            Divider()

            // Footer Toolbar
            HStack {
                Button(action: { model.testPhoneAlert() }) {
                    Label("Test Phone Alert", systemImage: "bell.badge")
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
        .frame(width: 360, height: 480)
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

// MARK: - Application Entry Point
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
