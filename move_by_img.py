"""
検出したい物体の入力から物体を検出し、少し近づき写真を取るスクリプト

"""
import cv2
import os
import argparse
import time
from olympe import Pdraw, PDRAW_YUV_FORMAT_I420, PDRAW_YUV_FORMAT_NV12, PdrawState
import sys
import numpy as np
import olympe
from olympe.messages.ardrone3.Piloting import TakeOff, Landing, moveTo, moveBy, Circle, PCMD
from olympe.messages.move import extended_move_by,extended_move_to
from olympe.messages.ardrone3.PilotingState import FlyingStateChanged, moveToChanged

#飛行した状態で物体検知(顔認証ができるかテスト)
DRONE_IP = "192.168.42.1"
ANAFI_IP = "192.168.42.1"



def yuv_frame_cb(yuv_frame,drone):
    """
    This function will be called by Olympe for each decoded YUV frame.
        :type yuv_frame: olympe.VideoFrame
    """
    # the VideoFrame.info() dictionary contains some useful information
    # such as the video resolution
    info = yuv_frame.info()
    height, width = info["yuv"]["height"], info["yuv"]["width"]

    # yuv_frame.vmeta() returns a dictionary that contains additional
    # metadata from the drone (GPS coordinates, battery percentage, ...)

    # convert pdraw YUV flag to OpenCV YUV flag
    cv2_cvt_color_flag = {
        PDRAW_YUV_FORMAT_I420: cv2.COLOR_YUV2BGR_I420,
        PDRAW_YUV_FORMAT_NV12: cv2.COLOR_YUV2BGR_NV12,
    }[info["yuv"]["format"]]

    # yuv_frame.as_ndarray() is a 2D numpy array with the proper "shape"
    # i.e (3 * height / 2, width) because it's a YUV I420 or NV12 frame

    # Use OpenCV to convert the yuv frame to RGB
    cv2frame = cv2.cvtColor(yuv_frame.as_ndarray(), cv2_cvt_color_flag)

    #灰色に変換して、imgにする
    img = cv2.cvtColor(cv2frame, cv2.COLOR_RGB2GRAY)
    img,info=Find_Detection(img)
    track_drone(info)

    # Use OpenCV to show this frame
    cv2.imshow("Olympe Pdraw Example", img)
    cv2.waitKey(1)  # please OpenCV for 1 ms...


fbRange = [6200, 6800]
pid = [0.4, 0.4, 0]
w, h = 360, 240
fb = 0


"""
カスケードフィルターの変更で検知する物体を変更可能
"""
def Find_Detection(img):
    # shift+右クリックでパスのコピーwinとlinux
    # face_cascade_path='C:\Users\manak\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs\home\manaki\awesome\mamoru\parrot2\haarcascade_frontalface_alt.xml'
    face_cascade_path = 'haarcascade_frontalface_alt.xml'
    wall_lack_cascade_path=''


    # カスケードファイルが存在するか
    if os.path.isfile(face_cascade_path) is False:
        print('ファイルが存在しない')
        return

    faceCascade = cv2.CascadeClassifier(face_cascade_path)
    # imgGray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    imgGray = img
    faces = faceCascade.detectMultiScale(imgGray, 1.2, 8)
    myFaceListC = []
    myFaceListArea = []
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 225), 2)
        cx = x + w // 2
        cy = y + h // 2
        area = w * h
        myFaceListC.append([cx, cy])
        myFaceListArea.append(area)
    #img⇛カラーに変換
    img=cv2.cvtColor(img, cv2.CV_GRAY2BGR)
    if len(myFaceListArea) != 0:
        i = myFaceListArea.index(max(myFaceListArea))
        return img, [myFaceListC[i], myFaceListArea[i]]
    else:
        return img, [[0, 0], 0]

def tracking(drone,info,w,pid,pError):
    x,y=info[0]
    area=info[1]
    fb=0

    ###この辺のコードの理解がまだ少し足りていない###
    error=x-w//2
    speed=pid[0]*error+pid[1]*(error-pError)
    speed=int(np.clip(speed,-100,100))
    if area>fbRange[0] and area<fbRange[1]:
        fb=0
    elif area>fbRange[1]:
        fb=-20
    elif area<fbRange[0] and area !=0:
        fb=20

    if x==0:
        speed=0
        error=0
    drone(extended_move_by(fb, 0, 0, speed, 1, 0.5, 0.5)
          >> FlyingStateChanged(state="hovering", _timeout=5)).wait().success()
    return error

def detail(drone,info,w,pid,pError):
    x,y=info[0]
    area=info[1]
    fb=0


def main(argv,drone):
    parser = argparse.ArgumentParser(description="Olympe Pdraw Example")
    parser.add_argument(
        "-u",
        "--url",
        default="rtsp://10.202.0.1/live",
        help=(
            "Media resource (rtsp:// or file://) URL.\n"
            "See olympe.Pdraw.play documentation"
        ),
    )
    parser.add_argument("-m", "--media-name", default="DefaultVideo")
    args = parser.parse_args(argv)
    pdraw = Pdraw()
    pdraw.set_callbacks(raw_cb=yuv_frame_cb(drone))
    pdraw.play(url=args.url, media_name=args.media_name)
    assert pdraw.wait(PdrawState.Playing, timeout=5)
    if args.url.endswith("/live"):
        # Let's see the live video streaming for 10 seconds
        time.sleep(10)
        pdraw.close()
        timeout = 5
    else:
        # When replaying a video, the pdraw stream will be closed automatically
        # at the end of the video
        # For this is example, this is the replayed video maximal duration:
        timeout = 90
    assert pdraw.wait(PdrawState.Closed, timeout=timeout)
    pdraw.dispose()

if __name__ == '__main__':
    drone = olympe.Drone("192.168.42.1")
    drone.connect()
    drone(TakeOff()).wait().success()
    drone(moveBy(0, 0, 0.5, 0)
        >> FlyingStateChanged(state="hovering", _timeout=5)).wait().success()
    main(sys.argv[1:],drone)

    assert drone(Landing()).wait().success()
    drone.disconnect()








