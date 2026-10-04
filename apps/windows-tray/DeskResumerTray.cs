using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text.Json;
using System.Windows.Forms;

namespace DeskResumer.WindowsTray
{
    public class TrayApplicationContext : ApplicationContext
    {
        private NotifyIcon trayIcon;
        private ContextMenuStrip contextMenu;
        private ToolStripMenuItem statusMenuItem;
        private ToolStripMenuItem queueMenuItem;
        private ToolStripMenuItem toggleWatchdogItem;
        private Timer pollTimer;
        private bool isWatchdogRunning = false;
        private string projectDir;

        public TrayApplicationContext()
        {
            projectDir = AppDomain.CurrentDomain.BaseDirectory;
            // Traverse up to find repo root if running from bin
            while (!File.Exists(Path.Combine(projectDir, "TASKS.md")) && Directory.GetParent(projectDir) != null)
            {
                projectDir = Directory.GetParent(projectDir).FullName;
            }

            InitializeComponents();
            RefreshState();

            pollTimer = new Timer();
            pollTimer.Interval = 3000;
            pollTimer.Tick += (s, e) => RefreshState();
            pollTimer.Start();
        }

        private void InitializeComponents()
        {
            contextMenu = new ContextMenuStrip();
            contextMenu.Font = new Font("Segoe UI", 9F);

            // Title Header
            var titleItem = new ToolStripMenuItem("DeskResumer // Supervisor");
            titleItem.Enabled = false;
            titleItem.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            contextMenu.Items.Add(titleItem);
            contextMenu.Items.Add(new ToolStripSeparator());

            // Status Info
            statusMenuItem = new ToolStripMenuItem("Channels: Checking...");
            statusMenuItem.Enabled = false;
            contextMenu.Items.Add(statusMenuItem);

            queueMenuItem = new ToolStripMenuItem("Queue: Checking...");
            queueMenuItem.Enabled = false;
            contextMenu.Items.Add(queueMenuItem);

            contextMenu.Items.Add(new ToolStripSeparator());

            // Actions
            toggleWatchdogItem = new ToolStripMenuItem("Start Watchdog", null, (s, e) => ToggleWatchdog());
            contextMenu.Items.Add(toggleWatchdogItem);

            var triggerTaskItem = new ToolStripMenuItem("Trigger Next Task", null, (s, e) => TriggerNextTask());
            contextMenu.Items.Add(triggerTaskItem);

            var openTasksItem = new ToolStripMenuItem("Open TASKS.md", null, (s, e) => OpenTasksFile());
            contextMenu.Items.Add(openTasksItem);

            var testAlertItem = new ToolStripMenuItem("Test Phone Alert", null, (s, e) => TestAlert());
            contextMenu.Items.Add(testAlertItem);

            contextMenu.Items.Add(new ToolStripSeparator());

            var exitItem = new ToolStripMenuItem("Exit DeskResumer", null, (s, e) => Exit());
            contextMenu.Items.Add(exitItem);

            // Generate Native Tray Icon (Geometric Hexagon)
            trayIcon = new NotifyIcon();
            trayIcon.Text = "DeskResumer - Autonomous Supervisor";
            trayIcon.Icon = CreateGeometricIcon(Color.MediumSeaGreen);
            trayIcon.ContextMenuStrip = contextMenu;
            trayIcon.Visible = true;
            trayIcon.DoubleClick += (s, e) => OpenTasksFile();
        }

        private Icon CreateGeometricIcon(Color dotColor)
        {
            using (var bmp = new Bitmap(16, 16))
            using (var g = Graphics.FromImage(bmp))
            {
                g.Clear(Color.Transparent);
                g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;

                // Draw outer dark badge
                using (var brush = new SolidBrush(Color.FromArgb(24, 28, 38)))
                {
                    g.FillEllipse(brush, 0, 0, 15, 15);
                }

                // Draw status dot
                using (var brush = new SolidBrush(dotColor))
                {
                    g.FillEllipse(brush, 4, 4, 7, 7);
                }

                return Icon.FromHandle(bmp.GetHicon());
            }
        }

        private string RunCli(string arguments)
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = $"-m desk_resumer.cli {arguments}",
                    WorkingDirectory = projectDir,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                };

                using (var proc = Process.Start(psi))
                {
                    string output = proc.StandardOutput.ReadToEnd();
                    proc.WaitForExit(3000);
                    return output;
                }
            }
            catch
            {
                return null;
            }
        }

        private void RefreshState()
        {
            string json = RunCli("status-json");
            if (string.IsNullOrEmpty(json)) return;

            try
            {
                using (var doc = JsonDocument.Parse(json))
                {
                    var root = doc.RootElement;
                    var targets = root.GetProperty("targets");
                    string chatgptState = "Offline";
                    string antigravityState = "Offline";
                    bool isLimited = false;

                    foreach (var t in targets.EnumerateArray())
                    {
                        string name = t.GetProperty("name").GetString();
                        bool running = t.GetProperty("running").GetBoolean();
                        bool limited = t.GetProperty("is_limited").GetBoolean();
                        bool busy = t.GetProperty("busy").GetBoolean();

                        if (limited) isLimited = true;

                        string state = !running ? "Offline" : (limited ? "Cooldown" : (busy ? "Busy" : "Ready"));
                        if (name.Contains("ChatGPT", StringComparison.OrdinalIgnoreCase)) chatgptState = state;
                        if (name.Contains("Antigravity", StringComparison.OrdinalIgnoreCase)) antigravityState = state;
                    }

                    var queue = root.GetProperty("queue");
                    int completed = queue.GetProperty("completed").GetInt32();
                    int total = queue.GetProperty("total").GetInt32();

                    statusMenuItem.Text = $"ChatGPT: {chatgptState} | Antigravity: {antigravityState}";
                    queueMenuItem.Text = $"Pipeline: {completed}/{total} Completed";

                    // Update Tray Icon Color
                    trayIcon.Icon = CreateGeometricIcon(isLimited ? Color.Orange : (isWatchdogRunning ? Color.MediumSeaGreen : Color.Gray));
                }
            }
            catch
            {
                // Ignore parse errors
            }
        }

        private void ToggleWatchdog()
        {
            isWatchdogRunning = !isWatchdogRunning;
            toggleWatchdogItem.Text = isWatchdogRunning ? "Stop Watchdog" : "Start Watchdog";
            string action = isWatchdogRunning ? "start" : "stop";
            RunCli($"service {action}");
            RefreshState();
        }

        private void TriggerNextTask()
        {
            RunCli("test-resume --app chatgpt");
            RefreshState();
        }

        private void OpenTasksFile()
        {
            string tasksPath = Path.Combine(projectDir, "TASKS.md");
            if (File.Exists(tasksPath))
            {
                Process.Start(new ProcessStartInfo("notepad.exe", tasksPath) { UseShellExecute = true });
            }
        }

        private void TestAlert()
        {
            RunCli("test-notify --message \"Hello from Windows Native System Tray!\"");
        }

        private void Exit()
        {
            trayIcon.Visible = false;
            pollTimer.Stop();
            Application.Exit();
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new TrayApplicationContext());
        }
    }
}
