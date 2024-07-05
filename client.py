#导入相关库
from PyQt5.QtCore import pyqtSignal,QObject
import time
from PyQt5.QtWidgets import *  
from Ui_client import Ui_MainWindow
from Ui_login import Ui_loginin
from Ui_boss import Ui_Dialog
from PyQt5.QtGui import QImage,QPixmap
import socket
import threading
import cv2
import sys 
import os
import numpy as np
import matplotlib.pyplot as plt
import struct
import pymysql
import pandas as pd
from multiprocessing import Process,Queue,Value
#全局变量
queuelist = Queue() #消息队列
charlist = [0,0] #进程间通信参数
matflag = [Value('i', 0) for _ in range(2)] #共享内存
speedval = 0.2 #速度大小绝对值
#管理员对话框类
class bosspas(QObject):
    #构造函数
    def __init__(self):
        super(bosspas,self).__init__()
        self.basapp = Ui_Dialog()
        self.form = QDialog()
        self.form.setWindowTitle('管理员权限')
        self.basapp.setupUi(self.form)
        self.basapp.pushButton.clicked.connect(self.close)   
    # 关闭窗口
    def close(self):
        if self.basapp.lineEdit.text() == 'qtz666':
            self.form.close()
        else: 
            msg_box = QMessageBox(QMessageBox.Warning, "警告", "密码错误,请重试")
            msg_box.exec_()
#小车参数类
class carinfo:
    linear_x = 0.0
    angual_z = 0.0
    odom_x = 0.0
    odom_y = 0.0
    odom_z = 0.0
    odom_w = 0.0
    yaw = 0
#登录类
class signup(QMainWindow):
    #构造函数
    def __init__(self):
        super(signup,self).__init__()
        
        self.logapp = Ui_loginin()
        self.form = QMainWindow()
        self.logapp.setupUi(self.form)
        self.form.setWindowTitle('登录')
        self.signflag = False
        self.loginflag = True
        self.logapp.login.clicked.connect(self.user_login)
        self.logapp.signup.clicked.connect(self.user_signup)
        self.logapp.password.setEchoMode(QLineEdit.Password)
        self.logapp.icon.setPixmap(QPixmap('smartcar_software/12.png').scaled(69,38))
        try:
            self.db = pymysql.connect(host="localhost",user="root", password="RQtz666.", database="mysql")
            self.cursor = self.db.cursor()
            print("数据库连接成功")
        except pymysql.Error as e:
            print("数据库连接失败"+str(e))
    #登录或者注册
    def user_login(self):
        #登录状态
        if self.loginflag:
            #查询数据库 
            nameval = self.logapp.username.text()
            sqlarry = f'SELECT * FROM car_user WHERE username=\'{nameval}\''
            self.cursor.execute(sqlarry)
            res = self.cursor.fetchall()
            if not res:
                msg = QMessageBox(QMessageBox.Warning,"警告","登录失败,用户名错误或用户不存在")
                msg.exec()
            else:
                if res[0][1] == self.logapp.password.text():
                    print("登录成功！")
                    #登陆成功,关闭数据库连接
                    self.db.close()
                    self.cursor.close()
                    self.form.close()
                    # 并启动主窗口
                    testr = client()
                    testr.myapp.statusBar.showMessage(f"当前用户：{nameval}")
                    testr.form.show()
                else:
                    msg = QMessageBox(QMessageBox.Warning,"提示","登录失败,密码错误")
                    msg.exec()
        #注册状态
        elif self.signflag:
            #将数据插入表格
            sql = 'INSERT INTO car_user (username,password) VALUE (%s,%s)'
            value  = (self.logapp.username.text(),self.logapp.password.text())
            self.cursor.execute(sql,value)
            self.db.commit()
            msg = QMessageBox(QMessageBox.Information,"提示","注册成功")
            msg.exec_()
            self.logapp.namelab.setText("用户名:")
            self.logapp.paslab.setText("密码:")
            self.logapp.login.setText("登录")
            self.loginflag = True
            self.signflag = False
    #点击注册
    def user_signup(self):
        self.loginflag = False
        self.signflag = True
        self.logapp.namelab.setText("注册用户名:")
        self.logapp.paslab.setText("注册密码:")
        self.logapp.login.setText("注册")
#客户端类
class client(QObject):
    #初始化信号
    show_vdieo = pyqtSignal(np.ndarray)
    show_data = pyqtSignal(float,str)
    show_mysqldata = pyqtSignal(str)
    show_carinfo = pyqtSignal(tuple)
    #构造函数
    def __init__(self):
       super(client,self).__init__()
       self.car = carinfo()
       self.myapp = Ui_MainWindow()
       self.form = QMainWindow()
       self.form.move(440,400)
       self.myapp.setupUi(self.form)
       self.myapp.iptext.setText("127.0.0.1")
       self.myapp.porttext.setText("8899")
       self.myapp.label_20.setPixmap(QPixmap("smartcar_software/12.png").scaled(69,38))
       self.myapp.disconnect.setDisabled(True)
       self.myapp.writeexcel.setDisabled(True)
       self.myapp.large.setDisabled(True)
    #    self.myapp.closechart.setDisabled(True)
    #    self.form.setMaximumSize(1113,735)
    #    self.form.setMinimumSize(1113,735)
        # 设置控件不可拉伸
       self.myapp.tabWidget_4.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
       self.myapp.dial.setRange(0,50)
       self.myapp.dial.setValue(20)
       self.myapp.dial.setSingleStep(2)
       self.myapp.comboBox.addItem("月光白")
       self.myapp.comboBox.addItem("暗夜黑")
       self.myapp.comboBox.addItem("闪耀蓝")
       self.myapp.comboBox.addItem("流光紫")
       self.myapp.comboBox.setCurrentIndex(0)
       self.form.setWindowTitle("client")
       msg_box = QMessageBox(QMessageBox.Information, "温馨提示", "请先点击连接服务器按扭，否则无法使用")
       msg_box.exec_()
      
       self.vdieo_flag = 3
       self.carinfo_flag = 3
       self.flag = True
       self.tcp_flag = False
       self.backcount  = 0
       self.chartflag = False
       self.closeflag  = False
       self.excelflag = False
       self.mysqlflag = False
       self.vdieo_value = b''
       self.car_value = b''
       self.aimdata =b''
       self.tempdata = b''
        #绑定信号和曹
       self.bind_singals()
    #  信号和草
    def bind_singals(self):
        self.myapp.start_server.clicked.connect(self.connect_server)
        self.myapp.video_accpect.stateChanged.connect(lambda state: self.ifshowvideoinfo(1) if state >= 1 else self.ifshowvideoinfo(2))
        self.myapp.writeexcel.stateChanged.connect(lambda state: self.ifsaveexcel(True) if state >= 1 else self.ifsaveexcel(False))
        self.myapp.disconnect.clicked.connect(self.disconnect)
        self.myapp.update.clicked.connect(self.showmatlob)
        self.myapp.closechart.clicked.connect( self.closechart)
        self.myapp.large.clicked.connect( self.chartpixmap)
        self.myapp.speed_accpect.stateChanged.connect(lambda state: self.ifshowcarinfo(1) if state >=1 else self.ifshowcarinfo(2))
        self.myapp.sendbtn.clicked.connect(self.sendtext_toserver)
        self.myapp.chart_accpect.stateChanged.connect(lambda state: self.showchart(1) if state >=1 else self.showchart(2))
        self.myapp.up.clicked.connect(lambda: self.sendlinearspeed_toserver(speedval))
        self.myapp.down.clicked.connect(lambda: self.sendlinearspeed_toserver(-speedval))
        self.myapp.right.clicked.connect(lambda: self.sendangualspeed_toserver(-speedval))
        self.myapp.left.clicked.connect(lambda: self.sendangualspeed_toserver(speedval))
        self.myapp.stop.clicked.connect(lambda: self.sendangualspeed_toserver(0))
        self.myapp.stop.clicked.connect( lambda: self.sendlinearspeed_toserver(0))
        self.myapp.send_loc.clicked.connect(lambda: self.send_loc(float(self.myapp.x_aim.text()),float(self.myapp.y_aim.text())))
        self.show_vdieo.connect(self.show_fream)
        self.show_data.connect(self.append_data)
        self.show_mysqldata.connect(self.append_mysqldata)
        self.show_carinfo.connect(self.append_carinfo)
        self.myapp.comboBox.currentIndexChanged.connect(lambda state: self.changebackground(state))
        self.myapp.dial.valueChanged.connect(lambda value: self.showdialval(value))
        self.myapp.mysql.clicked.connect(self.connect_mysql)
        self.myapp.excel.clicked.connect(self.importexcel)
        self.myapp.check_sqlspeedbtn.clicked.connect(self.checkspeed)
        self.myapp.check_sqluserbtn.clicked.connect(self.checkusers)
    #显示小车参数
    def append_carinfo(self,data):
        self.myapp.linea_text.setText(str(data[0])+"m/s")
        self.myapp.angual_text.setText(str(data[1])+"m/s")
        self.myapp.x_text.setText(str(data[2])+"m")
        self.myapp.y_text.setText(str(data[3])+"m")
        self.myapp.z_text.setText(str(data[4])+"m")
        self.myapp.w_text.setText(str(data[5])+"m")
        self.myapp.yaw_text.setText(str(data[6]))
       
        self.backcount += 1
        # print("999999")
        if self.backcount % 30 == 0 and self.chartflag:
            charlist[0] = data[0]
            charlist[1] = data[1]
            queuelist.put(charlist)
    #是否显示小车数据接收状态
    def ifshowcarinfo(self,value):
        self.carinfo_flag = value
        if value ==1:self.car = True
    #是否显示视频数据接收状态
    def ifshowvideoinfo(self,value):
        self.vdieo_flag = value
        if value ==1:self.video = True
    #添加数据
    def append_data(self,times,data):
        self.myapp.commuaction.append("["+str(times)+"]"+data)    
    #添加数据库数据
    def append_mysqldata(self,sqldata):
        self.myapp.mysqltext.append(sqldata)
    # 向服务器发送文本
    def sendtext_toserver(self):
        self.client_socket.sendall((0xDD).to_bytes(1,"little")+self.myapp.text.text().encode(encoding="utf-8"))
        self.show_data.emit(time.time(),f"客户端说：{self.myapp.text.text()}")
        self.myapp.text.clear()
    # 向服务器发送线速度
    def sendlinearspeed_toserver(self,value):
        self.client_socket.sendall((0xEE).to_bytes(1,"little")+str(value).encode(encoding="utf-8"))
        self.show_data.emit(time.time(),f"小车线速度:{str(value)}")
    # 向服务器发送角速度
    def sendangualspeed_toserver(self,value):
        self.client_socket.sendall((0xFF).to_bytes(1,"little")+str(value).encode(encoding="utf-8"))
        self.show_data.emit(time.time(),f"小车角速度:{str(value)}")
    #发送位置数据
    def send_loc(self,x,y):
        loc_val = struct.pack("ff",x,y)
        self.client_socket.sendall((0xFD).to_bytes(1,"little")+loc_val)
                                  
        self.show_data.emit(time.time(),f"x坐标: {self.myapp.x_aim.text()} y坐标: {self.myapp.y_aim.text()}")
    #连接服务器
    def connect_server(self):
        self.client_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.client_socket.connect((self.myapp.iptext.text(),int(self.myapp.porttext.text())))
        self.show_data.emit(time.time(),":服务器连接成功")
        #通知服务器可以发送数据
        self.client_socket.sendall((0xCC).to_bytes(1,"little"))
        #启动接收数据的线程，避免阻塞主线程
        self.th = threading.Thread(target=self.recv)
        self.th.start()    
        self.myapp.start_server.setDisabled(True)
        self.myapp.disconnect.setDisabled(False)
    #接收缓冲区数据
    def recv(self):
        while self.flag == True:
            data = self.client_socket.recv(88888) #收到数据，字节长度最大888888
            #收到服务器断开消息，break
            if data == b"exit": 
                self.show_data.emit(time.time(),":服务器断开连接")
                break
                
            if data[0:2] == 0x55aa.to_bytes(2,"little") or self.tcp_flag: #判断包头
                self.tcp_flag = True #第一次发送完整数据标志位
                if data[-2:] == 0x55cc.to_bytes(2,"little"): #判断包尾
                    self.aimdata = self.tempdata + data #将最后一次接收到的数据加上
                    longth = len(self.aimdata) #打印数据总长
                    video_length = longth- 36 #计算视频字节大小
                    # print(len(self.aimdata))
                    self.tcp_flag = False # 第一次发送完了完整数据后，标志位置0
                    if self.aimdata[2:6] == len(self.aimdata).to_bytes(4,"little"): #判断数据总长是否正确
                        dataval = struct.unpack('fffffff',self.aimdata[6:34]) #除去包头后的28位字节为小车参数
                        if self.carinfo_flag == 1 :
                            if self.car == True:
                                self.show_data.emit(time.time(),"开始接收小车参数") 
                                self.car = False #保证上述信号只发一次
                            self.show_carinfo.emit(dataval) #发送信号到主线程显示

                        elif self.carinfo_flag == 2 :
                            self.show_data.emit(time.time(),"停止接收小车参数")
                            self.carinfo_flag = 3
                             
                        self.vdieo_value = self.aimdata[34:34+video_length] #小车参数后的字节开始数video_length个字节为图像数据
                        nparry = np.frombuffer(self.vdieo_value,dtype="uint8")
                        fream = cv2.imdecode(nparry,cv2.IMREAD_COLOR) #视频帧解码

                        if fream is not None and self.vdieo_flag == 1:
                            if self.video  == True:
                                self.show_data.emit(time.time(),"开始接收视频参数")
                                self.video = False
                            self.show_vdieo.emit(fream) #将视频帧发送主线程显示

                        elif self.vdieo_flag == 2:
                            self.show_data.emit(time.time(),"停止接收视频参数")
                            self.vdieo_flag = 3 #保证上述信号只发一次
                    #第一次数据接收完成后字节段清空
                    self.tempdata = b''
                    self.aimdata = b''
                else:
                    self.tempdata += data #半包现象解决核心，没有到包尾就将字节拼接                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
    # 图像帧处理
    def show_fream(self,value):
         value = cv2.cvtColor(value,cv2.COLOR_BGR2RGB)
         height, width, channels = value.shape
        # 转换成QImage在 ui上显示
         images = QImage(value.data, width, height, width * channels, QImage.Format_RGB888)
         self.myapp.video.setPixmap(QPixmap.fromImage(images))
    #启动图表的进程
    def showchart(self,flag):
        if flag == 1:
            chart_timer = Process(target=self.drawchart,args=(queuelist,))
            chart_timer.start()
            self.chartflag = True
            self.show_data.emit(time.time(),"开始将数据转为图表")
            self.myapp.chart_accpect.setDisabled(True)
    #画图，使用队列和共享内存进行进程间通信
    def drawchart(self,arg):
        speed_count = 0
        plt.title("Linear Angular Velocity Variation Trend")
        plt.ylabel("Linear/Angular m/s")
        plt.xlabel("sec s")
        plt.grid(True)
        lx = []
        ax = []
        ly = []
        ay = []
            
        while True :  
            speed_count += 1
            res = arg.get()
            lx.append(speed_count)
            ax.append(speed_count)
            # speed,unit = self.myapp.linea_text.text().split("m")
            ly.append(res[0])
            ay.append(res[1])
            # plt.clf()
            plt.plot(lx,ly,color = "blue",label = 'Linear')
            plt.plot(ax,ay,color = "red",label = 'Angular')
            if speed_count == 1:  plt.legend()
            scope = speed_count / 60 
            # print("scope",scope)
            # 设置x轴刻度标签的显示间隔
            if scope % 1 == 0:
                plt.xlim(scope *60,scope *60 + 60)

            print(res[0],res[1])

            if matflag[0].value == 1:
                print("bye bye")
                #向主进程发送元组，每个为列表
                arg.put((lx,ly,ay))
                break
            if matflag[1].value == 1:
                plt.savefig('chartlist/chart.png')
                plt.savefig(f'chartlist/chart{speed_count}s.png')
                matflag[1].value = 0
            # time.sleep(1)
    #保存图表为图片     
    def showmatlob(self):  
        matflag[1].value = 1
        self.myapp.update.setDisabled(True)
        self.myapp.large.setDisabled(False)
    #关闭图表
    def closechart(self):
        matflag[0].value = 1
        self.closeflag  = True
        self.show_data.emit(time.time(),"关闭数据转为图表")
        self.myapp.writeexcel.setDisabled(False)
        time.sleep(0.5)#休眠0.5秒，为写入主进程提供时间 
    #将图表图片显示到qt窗口
    def chartpixmap(self):  
        self.myapp.chart.setPixmap(QPixmap("chartlist/chart.png"))
        self.myapp.update.setDisabled(False)
        self.myapp.large.setDisabled(True)
    #保存为excel表
    def ifsaveexcel(self,arg):
        if arg :
             #接收主进程数据
             sec,linear,angular = queuelist.get()
             writedata = {
                    '时间s' : sec,
                    '线速度m/s' : linear,
                    '角速度m/s' : angular
                    }
             fwrite = pd.DataFrame(writedata)
             fwrite.to_excel('laspeed.xlsx',index=False)
             self.show_data.emit(time.time(),"excel图表生成成功!文件名为laspeed.xlsx")
    #更换主题
    def changebackground(self,value):
        if  value == 0:
            self.form.setStyleSheet("background-color: rgb(255,255,255);color: rgb(0, 0, 0);")
        elif value == 1:
            self.form.setStyleSheet("background-color: rgb(46, 52, 54);color: rgb(255, 255, 255);")
            self.myapp.line.setStyleSheet("background-color: rgb(255, 255, 255);")
            self.myapp.line_2.setStyleSheet("background-color: rgb(255, 255, 255);")
            self.myapp.line_3.setStyleSheet("background-color: rgb(255, 255, 255);")
            self.myapp.line_4.setStyleSheet("background-color: rgb(255, 255, 255);")
            self.myapp.line_5.setStyleSheet("background-color: rgb(255, 255, 255);")
        elif value == 2:
            self.form.setStyleSheet("background-color: rgb(52, 101, 164);color: rgb(241, 232, 25);")
        elif value == 3:
            self.form.setStyleSheet("background-color: rgb(117, 80, 123);color: rgb(255, 255, 255);")
    #旋钮改变速度函数
    def showdialval(self,value):
        global speedval
        self.myapp.dial_lab.setText(str(value / 100)+"m/s")
        speedval = value / 100
    #连接数据库
    def connect_mysql(self):
        try:
            self.db = pymysql.connect(host="localhost",user="root", password="RQtz666.", database="mysql")
            self.cursor = self.db.cursor()
            self.mysqlflag = True
            self.show_mysqldata.emit("数据库连接成功")
        except pymysql.Error as e:
            self.show_mysqldata.emit("数据库连接失败"+str(e))
    #将excel表导入数据库
    def importexcel(self):
        if self.mysqlflag:
            if os.path.exists('laspeed.xlsx'):
                #导入前判断表中数据是否为空
                sqlsel = 'SELECT COUNT(*) FROM speed_trend'
                count = self.cursor.execute(sqlsel)
                if count > 0:
                    sqldel = 'DELETE FROM speed_trend'
                    self.cursor.execute(sqldel)
                    self.db.commit()
                    df = pd.read_excel('laspeed.xlsx')
                    #执行插入操作
                    sqlQuery = 'INSERT INTO speed_trend (sec,line,ang) VALUE (%s,%s,%s)'
                for k in range(1,len(df)):
                    sec = df.iloc[k,0]
                    linear_speed = df.iloc[k,1]
                    angular_speed = df.iloc[k,2]
                    value = (sec,linear_speed,angular_speed)
                    self.cursor.execute(sqlQuery,value)
                self.db.commit() 
                self.show_mysqldata.emit("导入成功！")
            else:
                self.show_mysqldata.emit("excel文件不存在")
        else:
             self.show_mysqldata.emit("数据库未连接")
    #查询数据库速度
    def checkspeed(self):
        if self.mysqlflag:
            timesec = self.myapp.sqlspeededit.text()
            if timesec == '':
                self.show_mysqldata.emit("查询列表为空，请正确输入整型数据 秒")
            else:
                sqlarry = f'SELECT * FROM speed_trend WHERE sec={int(timesec)}'
                clo = self.cursor.execute(sqlarry)
                res = self.cursor.fetchall()
                self.show_mysqldata.emit(f"线速度: {res[0][1]} m/s 角速度: {res[0][2]} m/s")
        else:
             self.show_mysqldata.emit("数据库未连接")
    #管理员权限查询用户密码
    def checkusers(self):
        if self.mysqlflag:
            #启动管理员窗口类
            bosspasword = bosspas()
            bosspasword.form.exec_()
            name = self.myapp.sqluseredit.text()
            sqlarry = f'SELECT * from car_user where username=\'{name}\''
            self.cursor.execute(sqlarry)
            res = self.cursor.fetchall()
            if not res:
                self.show_mysqldata.emit("查询失败,用户不存在")
            else:
                self.show_mysqldata.emit(f'用户名: {res[0][0]} 密码: {res[0][1]}')
        else:
            self.show_mysqldata.emit("数据库未连接")
    #断开socket连接
    def disconnect(self):
        if not self.closeflag :
             warn_box = QMessageBox(QMessageBox.Warning, "警告", "未关闭图表数据接收,点击OK关闭")
             result = warn_box.exec_()
             if result == QMessageBox.Ok:
                 #关闭子进程
                 matflag[0].value = 1
                 self.closeflag = True
                 self.show_data.emit(time.time(),"关闭数据转为图表")
        else:
            self.flag = False  
            self.client_socket.sendall("exit".encode(encoding="utf-8"))
            self.show_data.emit(time.time(),":客户端断开连接")
            time.sleep(0.5)
            #关闭socket
            self.client_socket.close()
        #若连接数据库，断开socket时关闭数据库
        if self.db.open and self.mysqlflag:
            self.db.close()
            self.cursor.close()
            self.show_data.emit(time.time(),"数据库断开连接")          
#主函数
if __name__ == "__main__":
    app  = QApplication(sys.argv)
    login = signup()
    login.form.show()     
    sys.exit(app.exec_())