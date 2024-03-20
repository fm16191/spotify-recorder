from datetime import datetime

def DOK(content):
    return print(f"\033[92m[{datetime.now().strftime('%Y %b.%d %H:%M:%S')}] {content}\033[0m"), True
def DINFO(content):
    print(f"\033[93m[{datetime.now().strftime('%Y %b.%d %H:%M:%S')}] {content}\033[0m")
def DERROR(content):
    return print(f"\033[91m[{datetime.now().strftime('%Y %b.%d %H:%M:%S')}] {content}\033[0m"), False
def OK(content):
    print(f"\033[92m{content}\033[0m")
def INFO(content):
    print(f"\033[93m{content}\033[0m")
def ERROR(content):
    return print(f"\033[91m{content}\033[0m")


class C:
    END = '\033[0m'

    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'

    LIGHTGRAY = '\033[37m'
    DARKGRAY = '\033[90m'
    LIGHTRED = '\033[91m'
    LIGHTGREEN = '\033[92m'
    LIGHTYELLOW = '\033[93m'
    LIGHTBLUE = '\033[94m'
    LIGHTMAGENTA = '\033[95m'
    LIGHTCYAN = '\033[96m'
    WHITE = '\033[97m'

    BG_WHITE = '\033[107m'
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46mCyan'

    BG_LIGHTGRAY = '\033[47m'
    BG_DARKGRAY = '\033[100m'
    BG_LIGHTRED = '\033[101m'
    BG_LIGHTGREEN = '\033[102m'
    BG_LIGHTYELLOW = '\033[103m'
    BG_LIGHTBLUE = '\033[104m'
    BG_LIGHTMAGENTA = '\033[105m'
    BG_LIGHTCYAN = '\033[106m'

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALIC = '\033[3m'
