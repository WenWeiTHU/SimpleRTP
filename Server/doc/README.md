# 服务端使用方法

* 依赖包

  > cv2
  >
  > pyqt5
  >
  > numpy

* 进入src文件夹,在videos文件夹下存放视频，支持 MP4, AVI, MOV, MKV, FLV格式

* 命令行下运行

```
# 先运行服务端
python server.py rtspport ftpport folder

# 例如
python server.py 554 521 videos
```

* 每经过一个周期，会进行RTCP报告，输出在控制台，格式如下
```
# 客户端输出
----- Sender Report -----
Version:  2
PT: 200
SSRC:  2873
Timestamp:  1575812370
NTP timestamp:  1575812370.0
Packet count:  5
Octet count:  13681117
```

```
# 服务端输出
----- Receiver Report -----
Version:  2
PT:  201
Reporter SSRC 2873
Reportee SSRC:  5729
Cumulative lost: 0
Sequence number:  5
Interval jitter:  1
LSR:  1575812370
DLSR:  0
```

* 支持多用户，另见Client/doc文件夹下README.md