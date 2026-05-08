#!/usr/bin/env python3
"""
Terminal Pomodoro Timer — 终端番茄钟
双击运行或在终端执行: python pomodoro.py
"""

import os, sys, time, json, threading, platform
from datetime import date
from pathlib import Path

# ── Dependency check ──────────────────────────────
def install_rich():
    import subprocess
    print('\n  正在安装 rich 库以提供精美界面...\n')
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'rich', '-q'])
    print('\n  安装完成！\n')

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    from rich.console import Console
    from rich.align import Align
    from rich.table import Table
    HAS_RICH = True
except ImportError:
    try:
        install_rich()
        from rich.live import Live
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.text import Text
        from rich.console import Console
        from rich.align import Align
        from rich.table import Table
        HAS_RICH = True
    except Exception:
        HAS_RICH = False

# ── Sound ──────────────────────────────────────────
if platform.system() == 'Windows':
    import winsound
    def play_sound():
        for freq in [523, 659, 784]:
            winsound.Beep(freq, 200)
else:
    def play_sound():
        print('\a', end='', flush=True)

# ── Config ─────────────────────────────────────────
CONFIG_DIR = Path.home() / '.pomodoro'
CONFIG_FILE = CONFIG_DIR / 'data.json'
DURATIONS = {'work': 25*60, 'break': 5*60, 'long': 15*60}
LABELS = {'work': '专注', 'break': '短休', 'long': '长休'}
ICONS = {'work': '🍅', 'break': '☕', 'long': '🌴'}

def load_data():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
    return {}

def save_data(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

# ── State ──────────────────────────────────────────
class PomodoroState:
    def __init__(self):
        self.mode = 'work'
        self.remaining = DURATIONS['work']
        self.total = DURATIONS['work']
        self.running = False
        self.sessions_today = 0
        self.today_str = date.today().isoformat()
        self._load()

    def _load(self):
        data = load_data()
        if data.get('date') == self.today_str:
            self.sessions_today = data.get('sessions', 0)
        else:
            self.sessions_today = 0

    def save(self):
        save_data({'date': self.today_str, 'sessions': self.sessions_today})

    def switch_mode(self, mode):
        self.running = False
        self.mode = mode
        self.remaining = DURATIONS[mode]
        self.total = DURATIONS[mode]

    def tick(self):
        if self.remaining > 0:
            self.remaining -= 1
            return self.remaining == 0
        return False

    def reset_current(self):
        self.running = False
        self.remaining = DURATIONS[self.mode]
        self.total = DURATIONS[self.mode]

    @property
    def progress(self):
        return 1 - (self.remaining / self.total)

    @property
    def time_str(self):
        m, s = divmod(self.remaining, 60)
        return f"{m:02d}:{s:02d}"

state = PomodoroState()

# ── Rich UI ────────────────────────────────────────
if HAS_RICH:
    console = Console()

    def make_layout():
        layout = Layout()
        layout.split(
            Layout(name='header', size=3),
            Layout(name='main', size=13),
            Layout(name='footer', size=5),
        )
        return layout

    def make_header():
        tabs = []
        for m in ('work', 'break', 'long'):
            color = 'red' if m == 'work' else ('green' if m == 'break' else 'blue')
            if m == state.mode:
                label = f'[bold {color}]● {LABELS[m]} {DURATIONS[m]//60}分[/bold {color}]'
            else:
                label = f'[dim]{LABELS[m]} {DURATIONS[m]//60}分[/dim]'
            tabs.append(label)
        return Panel('   '.join(tabs), border_style='bright_black')

    def make_main():
        icon = ICONS[state.mode]
        t = Text(f"{icon}  {state.time_str}", style='bold')
        t.stylize('white', 0, None)

        # ASCII progress bar
        bar_width = 40
        filled = int(state.progress * bar_width)
        bar_char = '█'
        empty_char = '░'
        bar_color = {'work': 'red', 'break': 'green', 'long': 'blue'}[state.mode]
        bar = f"[{bar_color}]{bar_char * filled}[/{bar_color}][dim]{empty_char * (bar_width - filled)}[/dim]"

        lines = [
            '',
            Align.center(t),
            '',
            Align.center(Text.from_markup(bar)),
            '',
            Align.center(Text.from_markup(
                f"[dim]{'▶ 运行中...' if state.running else '⏸ 已暂停'}   "
                f"进度: {int(state.progress * 100)}%[/dim]"
            )),
        ]
        return Panel('\n'.join(str(l) for l in lines), border_style='bright_black')

    def make_footer():
        table = Table(show_header=False, box=None, padding=(0, 4))
        table.add_column()
        table.add_column()
        table.add_column()
        table.add_column()
        table.add_row(
            '[bold]空格[/bold] [dim]开始/暂停[/dim]',
            '[bold]1/2/3[/bold] [dim]切换模式[/dim]',
            '[bold]R[/bold] [dim]重置[/dim]',
            '[bold]S[/bold] [dim]跳过[/dim]',
        )
        table.add_row(
            f'[bold]Q[/bold] [dim]退出[/dim]',
            '',
            '',
            f'🍅 × {state.sessions_today} [dim]今日番茄[/dim]',
        )
        table.add_row('', '', '', make_session_dots())
        return Panel(table, border_style='bright_black')

    def make_session_dots():
        dots = ''
        for i in range(4):
            if i < state.sessions_today % 4:
                dots += '[red]●[/red] '
            else:
                dots += '[dim]○[/dim] '
        return dots.strip()

    def render_ui():
        layout = make_layout()
        layout['header'].update(make_header())
        layout['main'].update(make_main())
        layout['footer'].update(make_footer())
        return layout

    def run_rich():
        import msvcrt

        with Live(render_ui(), console=console, screen=True, auto_refresh=False) as live:
            last_tick = time.time()
            while True:
                live.update(render_ui(), refresh=True)

                # Check for keypress (non-blocking)
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b' ':
                        state.running = not state.running
                        if state.running and state.remaining == 0:
                            state.reset_current()
                    elif key == b'\x1b':  # ESC
                        break
                    elif key.lower() == b'q':
                        break
                    elif key == b'1':
                        state.switch_mode('work')
                    elif key == b'2':
                        state.switch_mode('break')
                    elif key == b'3':
                        state.switch_mode('long')
                    elif key.lower() == b'r':
                        state.reset_current()
                    elif key.lower() == b's':
                        _skip()

                # Tick timer
                now = time.time()
                if state.running and now - last_tick >= 1:
                    finished = state.tick()
                    last_tick = now
                    if finished:
                        state.running = False
                        if state.mode == 'work':
                            state.sessions_today += 1
                            state.save()
                            threading.Thread(target=play_sound, daemon=True).start()
                        else:
                            threading.Thread(target=play_sound, daemon=True).start()

                time.sleep(0.05)

# ── Simple fallback UI ─────────────────────────────
def _skip():
    state.running = False
    state.remaining = 0
    if state.mode == 'work':
        state.sessions_today += 1
        state.save()
        if state.sessions_today % 4 == 0:
            state.switch_mode('long')
        else:
            state.switch_mode('break')
    else:
        state.switch_mode('work')

def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def format_bar(filled, width, mode):
    bar = '█' * filled + '░' * (width - filled)
    colors = {'work': '\033[91m', 'break': '\033[92m', 'long': '\033[94m'}
    c = colors[mode]
    return f"{c}{bar}\033[0m"

def render_simple():
    clear_screen()
    icon = ICONS[state.mode]
    label = LABELS[state.mode]
    bar_width = 40
    filled = int(state.progress * bar_width)
    status = '\033[93m▶ 运行中\033[0m' if state.running else '\033[90m⏸ 已暂停\033[0m'

    # Session dots
    dots = ''
    for i in range(4):
        if i < state.sessions_today % 4:
            dots += '\033[91m● \033[0m'
        else:
            dots += '\033[90m○ \033[0m'

    print(f"""
╔══════════════════════════════════════════════════╗
║               {icon}  {label} 番茄钟                  ║
╠══════════════════════════════════════════════════╣
║                                                    ║
║              {state.time_str}                        ║
║                                                    ║
║         {format_bar(filled, bar_width, state.mode)}   {int(state.progress*100)}%
║                                                    ║
║              {status}                              ║
║                                                    ║
╠════════════════════════════════════════════════════╣
║  空格 开始/暂停 │ 1/2/3 切换模式 │ R 重置 │ S 跳过  ║
║   🍅 今日番茄: {dots}  ×{state.sessions_today}         ║
║   Q 退出                                          ║
╚════════════════════════════════════════════════════╝
""")

def run_simple():
    import msvcrt
    last_tick = time.time()

    while True:
        render_simple()

        # Check for keypress (non-blocking, ~100ms polling)
        waited = 0
        while waited < 10:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b' ':
                    state.running = not state.running
                    if state.running and state.remaining == 0:
                        state.reset_current()
                elif key == b'\x1b' or key.lower() == b'q':
                    return
                elif key == b'1': state.switch_mode('work')
                elif key == b'2': state.switch_mode('break')
                elif key == b'3': state.switch_mode('long')
                elif key.lower() == b'r': state.reset_current()
                elif key.lower() == b's': _skip()
                break
            time.sleep(0.01)
            waited += 1

        # Tick
        now = time.time()
        if state.running and now - last_tick >= 1:
            finished = state.tick()
            last_tick = now
            if finished:
                state.running = False
                if state.mode == 'work':
                    state.sessions_today += 1
                    state.save()
                threading.Thread(target=play_sound, daemon=True).start()

# ── Entry ──────────────────────────────────────────
def main():
    if HAS_RICH:
        try:
            run_rich()
        except KeyboardInterrupt:
            pass
    else:
        try:
            run_simple()
        except KeyboardInterrupt:
            pass

    # Switch suggestion on completion
    if state.remaining == 0 and state.mode == 'work':
        clear_screen()
        print(f"\n  🍅 番茄完成！今日已完成 {state.sessions_today} 个番茄。")
        next_mode = 'long' if state.sessions_today % 4 == 0 else 'break'
        print(f"  建议进入 {LABELS[next_mode]} 模式 ({DURATIONS[next_mode]//60} 分钟)\n")
    elif state.remaining == 0:
        clear_screen()
        print(f"\n  休息结束！准备开始新的番茄吧 🍅\n")

if __name__ == '__main__':
    print()
    print('  🍅 Pomodoro Timer 启动中...')
    if not HAS_RICH:
        print('  (提示: pip install rich 可获得更精美的界面)')
    print()
    main()
