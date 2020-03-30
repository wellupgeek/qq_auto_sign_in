import win32con, win32gui
from PIL import ImageGrab
import os, time, re, json
from time import sleep
from aip import AipOcr
import logging
import logging.handlers
import win32clipboard as w


# 截图部分
class QQ_shot_screen(object):
    def __init__(self, name, savepath):
        self.name = name
        self.savepath = savepath

    def get_window_pos(self):
        handle = win32gui.FindWindow(0, self.name)
        # 获取窗口句柄
        if handle == 0:
            return None
        else:
            # 返回坐标值
            return win32gui.GetWindowRect(handle)

    def get_image(self):
        handle = win32gui.FindWindow(0, self.name)
        # 发送还原最小化窗口的信息
        win32gui.SendMessage(handle, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
        # 设为高亮
        win32gui.SetForegroundWindow(handle)
        x1, y1, x2, y2 = self.get_window_pos()
        image = ImageGrab.grab((x1, y1, x2, y2))
        # 截图
        return image

    def save_image(self, num=5, sleep_time=2, logger=None):
        now = time.strftime("%Y-%m-%d")
        dirpath = os.path.join(self.savepath, now)
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
            logger.info('创建文件夹: %s' %(dirpath))
        dirpath = os.path.join(dirpath, self.name)
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
            logger.info('创建文件夹: %s' %(dirpath))
        for i in range(1, num + 1):
            image = self.get_image()
            image.save(os.path.join(dirpath, self.name + '-' + str(i) + '.jpg'))
            logger.info('保存图片: %s' %(self.name + '-' + str(i) + '.jpg'))
            sleep(sleep_time)
        return dirpath


# 图片文字检测部分
class Detecter_pic(object):
    def __init__(self, det_path, key_word):
        self.det_path = det_path
        self.key_word = key_word

    # regex格式
    def get_regex(self, num, length):
        regex = [r'\d{1,' + str(length) + '}', '\w{1,' + str(length) + '}',
                 r'[\u96f6\u4e00\u4e8c\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341]{1,' + str(length) + '}']
        return regex[(num - 1) % 3]

    # 用于指定文字匹配模式
    def regrex_mode(self, mode_num, length):
        # 模式1：汉字/英文 + 数字（ex: 签到3）
        # 模式2：汉字/英文 + 英文（ex: 签到C or 签到c）
        # 模式3：汉字/英文 + 汉字数字（ex: 签到七）
        # 模式其它：自定义
        key_word = json.dumps(self.key_word).replace('"', '')
        regrex = self.get_regex(mode_num, length)
        nameRegex = re.compile(key_word + regrex)
        return nameRegex

    def detector(self, app_id, api_key, secret_key, mode_num=1, length=2, logger=None):
        APP_ID = app_id
        API_KEY = api_key
        SECRET_KEY = secret_key

        client = AipOcr(APP_ID, API_KEY, SECRET_KEY)
        start = time.time()
        logger.info('开始识别图片')

        # 选择匹配模式, 其key_word后接字符长度默认为2
        nameRegex = self.regrex_mode(mode_num, length)
        ans = []
        dirlist = os.listdir(self.det_path)
        dirlist.sort()
        num = 0
        for file in dirlist:
            num += 1
            image = open(os.path.join(self.det_path, file), 'rb')
            message = client.basicAccurate(image.read())
            # qps = 2 即每秒处理请求数为2
            if num % 2 == 0:
                time.sleep(1)
            end = time.time()
            logger.info('识别完成，共花时: %.2fs' %(end - start))
            words, temp = [], []
            for i in message.get('words_result'):
                words.append(str(i.get('words')).replace(' ', ''))

            text = '\n'.join(words)
            for group in nameRegex.findall(text):
                temp.append(group)
                logger.info('group = %s' %(group))
            temp.sort(reverse=True)
            if len(temp) > 0:
                ans.append(temp[0])
        return ans


# 发送消息部分
class Send_message(object):
    def __init__(self, name):
        self.name = name

    def sendAQQMessage(self, msg, logger=None):
        # 将测试消息复制到剪切板中
        w.OpenClipboard()
        w.EmptyClipboard()
        w.SetClipboardData(win32con.CF_UNICODETEXT, msg)
        w.CloseClipboard()
        logger.info('%s复制到剪切板中' %msg)
        # 获取窗口句柄
        handle = win32gui.FindWindow(0, self.name)
        # 还原
        win32gui.SendMessage(handle, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
        # 设为高亮
        win32gui.SetForegroundWindow(handle)
        # 填充消息
        win32gui.SendMessage(handle, 770, 0, 0)
        logger.info('在(%s)窗口中填充消息:%s' %(self.name, msg))
        # 回车发送消息
        win32gui.SendMessage(handle, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        logger.info('回车发送')
        win32gui.SetBkMode(handle, win32con.TRANSPARENT)
        win32gui.ShowWindow(handle, win32con.SW_MINIMIZE)


# 专门解决汉字数字与数字之间的转换
class Convert(object):
    def __init__(self):
        hanzi = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '百']
        number = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]
        self.han_num = list(zip(hanzi, number))

    def pop(self, temp, num):
        temp.remove(num)
        while len(temp) < len(str(num)):
            temp.append(0)

    def hanzi_to_number(self, convert_str):
        temp = []
        for i in range(len(convert_str)):
            symbol = convert_str[i]
            for hanzi, number in self.han_num:
                if symbol == hanzi:
                    temp.append(number)
                    break
        if 10 in temp and 100 in temp:
            self.pop(temp, 10)
            self.pop(temp, 100)
        elif 10 in temp and 100 not in temp:
            self.pop(temp, 10)
        elif 10 not in temp and 100 in temp:
            self.pop(temp, 100)
        sum = 0
        for i in range(len(temp)):
            sum += temp[i] * (10 ** (len(temp) - 1 - i))
        return sum

    def number_to_hanzi(self, convert_num):
        temp, count = [], 0
        new_num = convert_num
        while new_num > 0:
            base = 10 ** count
            if base > 1:
                temp.append(base)
            temp.append(new_num % 10)
            new_num //= 10
            count += 1
        index = len(temp) - 1
        str_text = []
        while index >= 0:
            symbol = temp[index]
            for hanzi, number in self.han_num:
                if symbol == number:
                    str_text.append(hanzi)
                    break
            index -= 1
        return ''.join(str_text)

# 日志记录
def setMyLogger(Filename, log):
    log.setLevel(logging.INFO)
    file_handle = logging.handlers.RotatingFileHandler(Filename, mode='a', maxBytes=10241024, backupCount=5, encoding='utf-8')
    fmt = '%(asctime)s %(levelname)s %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S'
    formater = logging.Formatter(fmt=fmt, datefmt=datefmt)
    file_handle.setFormatter(formater)
    log.addHandler(file_handle)

# 只发送固定短语，无需检测之前发送的内容
def function_one(win_list, logger):
    send_obj = Send_message(win_list[0])
    send_obj.sendAQQMessage(win_list[1], logger)


def function_two(win_list, others_list, logger):
    variables = ['num', 'sleep_time', 'save_path', 'APP_ID', 'API_KEY', 'SECRET_KEY']
    var_dict = {variables[i]: others_list[i] for i in range(6)}

    win_vars = ['win_name', 'key_word', 'mode', 'max_len']
    win_dict = {win_vars[i]: win_list[i] for i in range(4)}

    qqshot = QQ_shot_screen(name=win_dict['win_name'], savepath=var_dict['save_path'])
    dirpath = qqshot.save_image(num=int(var_dict['num']), sleep_time=int(var_dict['sleep_time']), logger=logger)

    det_obj = Detecter_pic(det_path=dirpath, key_word=win_dict['key_word'])
    ans = det_obj.detector(app_id=var_dict['APP_ID'], api_key=var_dict['API_KEY'], secret_key=var_dict['SECRET_KEY'],
                           mode_num=int(win_dict['mode']), length=int(win_dict['max_len']), logger=logger)
    strtext = ans[-1]
    msg = win_dict['key_word']
    mode, length = int(win_dict['mode']), int(win_dict['max_len'])
    start_len = len(msg)

    if len(ans) > 0:
        if mode == 1:  # 模式1 汉字/英文 + 数字
            logger.info('模式1')
            num = int(strtext[start_len:]) + 1
            msg += str(num)
        elif mode == 2:  # 模式2  汉字/英文 + 英文（ex: 签到C or 签到c)
            logger.info('模式2')
            uni_num = ord(strtext[start_len:])
            if 65 <= uni_num < 90 or 97 <= uni_num < 122:
                msg += chr(uni_num + 1)  # 此处默认A-Z，a-z
        elif mode == 3:  # 汉字/英文 + 汉字数字（ex: 签到七、签到八一、签到八十一）
            logger.info('模式3')
            text = strtext[start_len:]
            num = Convert().hanzi_to_number(text)
            msg += Convert().number_to_hanzi(num + 1)

    send_obj = Send_message(win_dict['win_name'])
    send_obj.sendAQQMessage(msg, logger=logger)


def main():
    logFile = 'record.log'
    log = logging.getLogger()
    setMyLogger(logFile, log)

    fp = open("document.txt", 'r', encoding='utf-8')
    cont = fp.read()
    pattern = re.compile("'(.*)'")
    contRe = pattern.findall(cont)
    fp.close()

    # 获取对应窗口及相应窗口的功能
    window_name_list = contRe[0].split(';')
    choose_list = contRe[1].split(';')
    key_words_list = contRe[2].split(';')
    mode_list = contRe[3].split(';')
    max_len_list = contRe[4].split(';')
    others_list = contRe[5:]
    while len(choose_list) < len(window_name_list):
        choose_list.append('1')
    for index in range(len(choose_list)):
        if choose_list[index] == '1':
            temp = (window_name_list[index], key_words_list[index])
            function_one(temp, log)
        if choose_list[index] == '2':
            temp = (window_name_list[index], key_words_list[index], mode_list[index], max_len_list[index])
            function_two(temp, others_list, log)


if __name__ == '__main__':
    main()
