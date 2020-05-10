import sys

from PyQt5.QtWidgets import(QWidget, QGridLayout, QApplication,QLabel,QHBoxLayout,QVBoxLayout,QComboBox,QTextEdit,QPushButton,QSlider,QFileDialog)
from PyQt5.QtGui import (QPixmap,QIcon)
from PyQt5.QtCore import (Qt,pyqtSignal)
from aip import AipOcr
from PIL import Image
from aip import AipSpeech
from threading import Thread
import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os


BTN_MIN_WIDTH = 120

#百度api相关的信息可以再百度上申请
APP_ID = ['197xxx','197xxxx']  # 刚才获取的 ID，下同
API_KEY = ['UBvIqTtxxxx','nqfXbP4pwmxxxxxx']
SECRECT_KEY = ['3jyCNeDTWayknxxxxxxx','EVqpPX650sgY8hxxxxxxxx']
client = AipOcr(APP_ID[0], API_KEY[0], SECRECT_KEY[0])
clientAudio = AipSpeech(APP_ID[1], API_KEY[1], SECRECT_KEY[1])



#用于控制音色的，一个百度的一个科大讯飞的
audioTypeb={"女声":0, "男声":1, "感情合成-男":2,"感情合成-女":3}
audioTypek={"讯飞小燕":'xiaoyan', "讯飞许久":'aisjiuxu', "讯飞小萍":'aisxping',"讯飞小婧":'aisjinger',"讯飞许小宝":'aisbabyxu'}

#全局变量
playing = False
paused = False
thead=''
thead2=''

import pyaudio
import wave

from pydub import AudioSegment

#用于保存音频的文件
audioFilemp3='audio.mp3'
audioFilewav='audio.wav'

import logging
from os import path
#日志模块
class Logger:
    def __init__(self,filname):
        self.log_file_path = path.join(path.dirname(path.abspath(__file__)), filname)
        self.filename = filname
    def get_logger(self, verbosity=1, name=None):
        level_dict = {0: logging.DEBUG, 1: logging.INFO, 2: logging.WARNING}
        # formatter = logging.Formatter(
        #     "[%(asctime)s][%(filename)s][%(funcName)s][line:%(lineno)d][%(levelname)s] %(message)s"
        # )
        formatter = logging.Formatter(
            "[%(asctime)s][%(funcName)s][line:%(lineno)d][%(levelname)s] %(message)s"
        )
        logger = logging.getLogger(name)
        logger.setLevel(level_dict[verbosity])

        fh = logging.FileHandler(self.log_file_path, "w")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        return logger

log = Logger('runlog.log').get_logger()
#Mp3转wav
def mp3Towav():
    # print("strat to")
    log.info(" mp3Towav strat")
    # if path.exists(audioFilewav):
    #     os.remove(audioFilewav)
    if path.exists(audioFilemp3):
        song = AudioSegment.from_mp3(audioFilemp3)
        song.export(audioFilewav, format="wav")
        log.info(" mp3Towav finished")
        # print("end to")
    else:
        log.info(" mp3Towav nofile")
        # print('nofile')

#音频播放模块使用的pyaudio
class audioPlay():
    def __init__(self):
        self.wf=''
        self.pl=''
        self.stream=''
    def openfile(self):
        if path.exists(audioFilewav):
            self.wf = wave.open(audioFilewav, 'rb')
        else:
            self.w=''
    def setpl(self):
        self.pl = pyaudio.PyAudio()
    def setstream(self):
        self.stream = self.pl.open(format=self.pl.get_format_from_width(self.wf.getsampwidth()),
                        channels=self.wf.getnchannels(),
                        rate=self.wf.getframerate(),
                        output=True,
                        stream_callback=self.callback)

    def callback(self,in_data, frame_count, time_info, status):
        data = self.wf.readframes(frame_count)
        return (data, pyaudio.paContinue)
    def stramStart(self):
        self.stream.start_stream()
    def stremStop(self):
        self.stream.stop_stream()

    def startplay(self):
        global playing
        log.info("play start")
        self.openfile()
        if self.wf=='':
            # print("not have file")
            log.info("not have file")
            return
        self.setpl()

        self.setstream()
        self.stramStart()
        playing = True
        while self.stream.is_active() or paused == True:
            pass
        log.info("play finished")
    def  stram_is_stoped(self):
        return self.stream.is_stopped()
    def stream_is_active(self):
        return self.stream.is_active()
    def stopPlay(self):
        global playing
        global paused
        if self.stream.is_active():
            self.stream.stop_stream()
        self.stream.close()
        self.wf.close()
        # close PyAudio
        self.pl.terminate()
        playing=False
        paused=False

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

auply=audioPlay()
#科大讯飞的音频合成模块中初始化参数与拼接URL
class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Text,vcn,speed):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text
        self.vcn = vcn
        self.speed = speed

        # 公共参数(common)
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {"aue": "lame","sfl":1,"auf": "audio/L16;rate=16000", "vcn":str(self.vcn) , "tte": "utf8","speed":int(self.speed)}
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")}

    # 生成url
    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        # 进行hmac-sha256进行加密
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        # 将请求的鉴权参数组合为字典
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        # 拼接鉴权参数，生成url
        url = url + '?' + urlencode(v)
        return url



#科大讯飞的音频合成模块中进行网络数据请求
class kedaxunfei():
    def __init__(self,text,vcn,speed):
        self.text = text
        self.vcn = vcn
        self.speed = speed
        self.wsParam=''
        self.wsUrl=''
        self.ws=''
    def stratPlay(self):
        self.wsParam = Ws_Param(APPID='5exxxxxx', APIKey='9db00a4c1c5xxxxxxxxx',
                                APISecret='bec6b6167a2228xxxxxxx',
                                Text=self.text, vcn=self.vcn, speed=self.speed)
        websocket.enableTrace(False)
        self.wsUrl = self.wsParam.create_url()
        self.ws = websocket.WebSocketApp(self.wsUrl, on_message=self.on_message, on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws.on_open = self.on_open
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        # print("llllllllll")

    def on_open(self):
        global thead
        def run(*args):
            d = {"common": self.wsParam.CommonArgs,
                 "business": self.wsParam.BusinessArgs,
                 "data": self.wsParam.Data,
                 }
            d = json.dumps(d)
            # print("------>开始发送文本数据")
            self.ws.send(d)
            global playing
            if playing == True:
                log.info("playing")
                auply.stopPlay()
            if os.path.exists(audioFilemp3):
                try:
                    os.remove(audioFilemp3)
                except IOError:
                    log.info('文件被占用')

        thread.start_new_thread(run, ())

    def on_message(self, message):
        try:
            message = json.loads(message)
            code = message["code"]
            sid = message["sid"]
            audio = message["data"]["audio"]
            audio = base64.b64decode(audio)
            status = message["data"]["status"]
            # print(message)
            if status == 2:
                log.info("ws is closed")
                self.ws.close()
            if code != 0:
                errMsg = message["message"]
                # print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
                log.info("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
            else:
                with open(audioFilemp3, 'ab') as f:
                    f.write(audio)
        except Exception as e:
            # print("receive msg,but parse exception:", e)
            log.info("receive msg,but parse exception:", e)


    # 收到websocket错误的处理
    def on_error(self,ws, error):
        print("### error:", error)

    # 收到websocket关闭的处理
    def on_close(self,ws):
        print("### closed ###")

    def playAutio(self):
        global playing
        global thead
        if playing==True:
            # print("playing")
            log.info("playing")
            auply.stopPlay()
        mp3Towav()
        auply.startplay()
    def playRun(self):
        log.info('keda audio')
        self.stratPlay()
        self.playAutio()



#自定义label
class MyLabel(QLabel):
    sendMsg = pyqtSignal(str)
    def __init__(self):
        super().__init__()
    def mousePressEvent(self, e):
        objectname = self.objectName()
        self.sendMsg.emit(objectname)


#百度语音合成模块
class baidu:
    def __init__(self,text,pre,speed):
        self.text = str(text).encode('utf-8')
        self.pre = pre
        self.speed = speed
    def playAutio(self):
        global thead
        global playing
        if playing==True:
            auply.stopPlay()
        if os.path.exists(audioFilemp3):
            try:
                os.remove(audioFilemp3)
            except IOError:
                # print('文件被占用')
                log.info('文件被占用')
        result = clientAudio.synthesis(self.text, 'zh', 1, {
            'per': self.pre,
            'spd': self.speed,  # 速度
            'vol': 7  # 音量
        })
        if not isinstance(result, dict):
            with open(audioFilemp3, 'wb') as f:
                f.write(result)
            mp3Towav()
        else:
            print(result)
        log.info('baidu audio')
        auply.startplay()

#主窗口与布局
class MainLayout(QVBoxLayout):
    """主要布局"""
    def __init__(self, parent):
        super().__init__()
        #初始化默认参数
        self.textdata=''
        self.audioTypeidb = 0
        self.audioSpeedidb = 5

        self.audioTypeidk = 0
        self.audioSpeedidk = 50
        #获取屏幕大小
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.height = self.screenRect.height()-150
        self.width = self.screenRect.width()

        self.heighti = (self.height)/5
        self.widthi = (self.width)/3

        self.parent = parent
        #设置布局
        self.VLayout = QVBoxLayout()
        self.HLayout = QHBoxLayout()
        self.GLayout = QGridLayout()
        #添加文本框
        self.textW =QTextEdit("内容显示")
        # self.textW.resize(self.width/3,self.height-500)
        self.HLayout.addLayout(self.GLayout)
        self.HLayout.addWidget(self.textW)
        self.file_name = None
        #

        #图片上传按钮
        upload_btn = QPushButton("上传图片")
        upload_btn.setMinimumWidth(50)
        upload_btn.clicked.connect(self.on_upload)
        upload_btn.setStyleSheet("font-weight:bold;")

        #百度语音速度滑动条
        self.lb = QLabel()
        self.lb.setText("百度语音速度")
        # 设置水平方向显示
        self.slb = QSlider(Qt.Horizontal)
        # 设置最小值
        self.slb.setMinimum(1)
        # 设置最大值
        self.slb.setMaximum(10)
        # 设置步长
        self.slb.setSingleStep(1)
        # 设置当前值
        self.slb.setValue(5)
        # 设置在水平滑块下方绘制刻度线
        self.slb.setTickPosition(QSlider.TicksBelow)
        # 设置刻度间隔
        self.slb.setTickInterval(2)
        self.slb.valueChanged.connect(self.valuechangeb)

        # 科大语音速度滑动条
        self.lk = QLabel()
        self.lk.setText("科大语音速度")
        # 设置水平方向显示
        self.slk = QSlider(Qt.Horizontal)
        # 设置最小值
        self.slk.setMinimum(1)
        # 设置最大值
        self.slk.setMaximum(100)
        # 设置步长
        self.slk.setSingleStep(1)
        # 设置当前值
        self.slk.setValue(50)
        # 设置在水平滑块下方绘制刻度线
        self.slk.setTickPosition(QSlider.TicksBelow)
        # 设置刻度间隔
        self.slk.setTickInterval(2)
        self.slk.valueChanged.connect(self.valuechangek)


        self.save_btn = QPushButton("百度播放")
        self.save_btn.setMinimumWidth(50)
        self.save_btn.clicked.connect(self.baiduPlay)
        self.save_btn.setStyleSheet("font-weight:bold;")
        self.audio_type = QComboBox()
        self.audio_type.addItems(['女声', '男声', '感情合成-男','感情合成-女'])
        self.audio_type.currentIndexChanged.connect(self.selectionchange)


        self.save_btn_ke = QPushButton("科大讯飞播放")
        self.save_btn_ke.setMinimumWidth(50)
        self.save_btn_ke.clicked.connect(self.kedaplay)
        self.save_btn_ke.setStyleSheet("font-weight:bold;")
        self.audio_type_ke = QComboBox()
        self.audio_type_ke.addItems(["讯飞小燕", "讯飞许久", "讯飞小萍","讯飞小婧","讯飞许小宝"])
        self.audio_type_ke.currentIndexChanged.connect(self.selectionchangek)

        self.ply_btn = QPushButton("暂定/播放")
        self.ply_btn.setMinimumWidth(100)
        self.ply_btn.clicked.connect(self.ply_stop)
        self.ply_btn.setStyleSheet("font-weight:bold;")


        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        btn_layout.addWidget(upload_btn)
        btn_layout.addWidget(self.lb)
        btn_layout.addWidget(self.slb)
        btn_layout.addWidget(self.audio_type)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.ply_btn)
        btn_layout.addWidget(self.lk)
        btn_layout.addWidget(self.slk)
        btn_layout.addWidget(self.audio_type_ke)
        btn_layout.addWidget(self.save_btn_ke)


        self.VLayout.addLayout(self.HLayout)
        self.VLayout.addLayout(btn_layout)
        self.addLayout(self.VLayout)

    #显示图片16张图片是4x4显示
    def setQImage(self,fileList):
        i = 0
        len1 = len(fileList)
        print("len:",len1)
        for x in range(4):
            for y in range(4):
                label = MyLabel()
                label.sendMsg.connect(self.chilkImage)
                pixmap = QPixmap(fileList[i]).scaled(160,150)
                label.setPixmap(pixmap)
                label.setObjectName(str(fileList[i]))
                label.setMouseTracking(True)
                self.GLayout.addWidget(label, x, y)
                i += 1
                if i>=len1:
                    return
    #百度音色下拉框事件函数
    def selectionchange(self):
        global audioTypeb
        self.audioTypeidb = audioTypeb[self.audio_type.currentText()]
        print(self.audioTypeidb)

    # 科大音色下拉框事件函数
    def selectionchangek(self):
        global audioTypek
        self.audioTypeidk = audioTypek[self.audio_type_ke.currentText()]
        print(self.audioTypeidk)

    # 百度声速滑动条事件函数
    def valuechangeb(self):
        self.audioSpeedidb = self.slb.value()
        print(self.audioSpeedidb)

    # 科大声速滑动条事件函数
    def valuechangek(self):
        self.audioSpeedidk = self.slk.value()
        print(self.audioSpeedidk)
    #加载图片文件事件
    def on_upload(self):
        img_paths, _ = QFileDialog.getOpenFileNames(self.parent, "Open image",
                                                  "/Users",
                                                  "Images (*.png *jpg)")
        # print("img_paths:",img_paths)
        log.info("img_paths:",img_paths)
        if len(img_paths)!=0:
            self.setQImage(img_paths)

    #点击图片事件
    def chilkImage(self,filename):
        # global thead
        outfile = 'export.txt'
        self.save_btn.setEnabled(False)
        self.save_btn_ke.setEnabled(False)
        self.baiduOCR(filename, outfile)
    #图片压缩
    def convertimg(self,picfile, outdir):
        '''调整图片大小，对于过大的图片进行压缩
        picfile:    图片路径
        outdir：    图片输出路径
        '''
        img = Image.open(picfile)
        width, height = img.size
        while (width * height > 4000000):  # 该数值压缩后的图片大约 两百多k
            width = width // 2
            height = height // 2
        new_img = img.resize((width, height), Image.BILINEAR)
        new_img.save(path.join(outdir, os.path.basename(picfile)))

    #图片内容识别模块
    def baiduOCR(self,picfile, outfile):
        """利用百度api识别文本，并保存提取的文字
        picfile:    图片文件名
        outfile:    输出文件
        """
        print(picfile)
        arr = []
        arr2 = []

        data = ''
        self.textdata =''
        filename = path.basename(picfile)
        i = open(picfile, 'rb')
        img = i.read()
        # print("正在识别图片：\t" + filename)
        log.info("正在识别图片：\t" + filename)
        # message = client.basicGeneral(img)  # 通用文字识别，每天 50 000 次免费
        message = client.basicAccurate(img)  # 通用文字高精度识别，每天 800 次免费
        # print("识别成功！")
        log.info("识别成功")
        i.close()
            # 输出文本内容
        for text in message.get('words_result'):
            temdata = text.get('words')
            arr.append(temdata)
            arr2.append(temdata+'\n')
        data = data.join(arr2)
        self.textdata=self.textdata.join(arr)
        self.textW.setText(data)
        self.save_btn.setEnabled(True)
        self.save_btn_ke.setEnabled(True)
        # print("文本导出成功！")
        log.info("文本导出成功！函数结束")
    #百度播放事件 另起线程防止主窗口卡死
    def baiduPlay(self):
        if len(self.textdata)>0:
            global thead2
            baiduplay = baidu(self.textdata,self.audioTypeidb,self.audioSpeedidb)
            thead2 = Thread(target=baiduplay.playAutio)
            thead2.start()
            # baiduplay.playAutio()
    #科大播放事件
    def kedaplay(self):
        if len(self.textdata)>0:
            global thead2
            keda = kedaxunfei(self.textdata,self.audioTypeidk,self.audioSpeedidk)
            # keda.playAutio()
            thead2 = Thread(target=keda.playRun)
            thead2.start()
    #播放与暂定播放事件
    def ply_stop(self):
        global paused
        global playing
        if playing:
            if auply.stram_is_stoped():

                auply.stramStart()
                paused = False
            # time to pause audio
            elif auply.stream_is_active():
                print('pause pressed')
                auply.stremStop()
                paused = True


#主窗口
class MainWin(QWidget):
    def __init__(self):
        super().__init__()
        self.desktop = QApplication.desktop()
        self.screenRect = self.desktop.screenGeometry()
        self.height = self.screenRect.height()
        self.width = self.screenRect.width()
        self.main_layout = MainLayout(self)
        self.setLayout(self.main_layout)
        self.initUI()
    def initUI(self):
        self.showMaximized()
        self.move(10, 0)
        self.resize(self.width, self.height-100)
        self.setWindowTitle("谷德谷德思达滴，呆呆嗨皮")
        self.setWindowIcon(QIcon("ico.jpg"))
    def moveEvent(self,event):
        self.resize(self.width, self.height-100)

    def closeEvent(self, event):
        if playing==True:
            auply.stopPlay()
        if os.path.exists(audioFilemp3):
            try:
                os.remove(audioFilemp3)
            except IOError:
                log.log('文件被占用')
                # print('文件被占用')
        if os.path.exists(audioFilewav):
            try:
                os.remove(audioFilewav)
            except IOError:
                log.log('文件被占用')





app = QApplication(sys.argv)
Mymain = MainWin()
Mymain.setWindowFlags(Qt.WindowMinimizeButtonHint)
Mymain.setWindowFlags(Qt.WindowCloseButtonHint)
# Mymain.setFixedSize(Mymain.width(), Mymain.height())


Mymain.show()
sys.exit(app.exec_())

