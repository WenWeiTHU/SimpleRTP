import cv2, numpy, sys, re


def frameDecode(buf):
    """Image decode with OpenCV """
    # print(sys.getsizeof(buf))
    img = numpy.frombuffer(buf, dtype=numpy.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)
    return img

def frameEncode(frame, quality):
    """Image eecode with OpenCV"""
    ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    buf = bytearray(buf)
    # print(sys.getsizeof(buf))
    if not ok:
        print('encode failed')
    return buf

def formatPlayTime(frameNbr, frameTotal, fps):
    """Display time-line by frame total, current frame and FPS"""
    m, s = divmod(frameTotal / fps, 60)
    h, m = divmod(m, 60)
    timeTotal = "%02d:%02d:%02d" % (h, m, s)
    m, s = divmod(frameNbr / fps, 60)
    h, m = divmod(m, 60)
    timeNow = "%02d:%02d:%02d" % (h, m, s)
    return "%s/%s" % (timeNow, timeTotal)


def readSrt(filename):
    text = open(filename, encoding='utf-8')

    rgx_time = re.compile(r'(\d\d:\d\d:\d\d),\d\d\d --> (\d\d:\d\d:\d\d),\d\d\d\n([^\n]*)\n')
    rgx_line = re.compile(r'\{[^\}]*\}')

    dic = {}

    lines = rgx_time.findall(text.read())
    for line in lines:
        words = rgx_line.sub('', line[2])
        dic[line[0]] = words

    return dic