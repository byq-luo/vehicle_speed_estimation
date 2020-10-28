#!/usr/bin/env python

'''
Lucas-Kanade tracker
====================
Lucas-Kanade sparse optical flow demo. Uses goodFeaturesToTrack
for track initialization and back-tracking for match verification
between frames.
Usage
-----
lk_track.py [<video_source>]
Keys
----
ESC - exit
'''

# Python 2/3 compatibility
from __future__ import print_function
import matplotlib.pyplot as plt
import numpy as np
import cv2 as cv
import math

import video
from common import anorm2, draw_str

lk_params = dict( winSize  = (15, 15),
                  maxLevel = 2,
                  criteria = (cv.TERM_CRITERIA_EPS | cv.TERM_CRITERIA_COUNT, 10, 0.03))

feature_params = dict( maxCorners = 500,
                       qualityLevel = 0.3,
                       minDistance = 7,
                       blockSize = 7 )

fps = 30
px2m1 = 0.0895
px2m2 = 0.088
px2m3 = 0.0774
px2m4 = 0.0767
px2m5 = 0.0736
ms2kmh = 3.6
class App:
    def __init__(self, video_src):
        self.track_len = 2
        self.detect_interval = 2
        self.tracks = []
        self.cam = video.create_capture(video_src)
        self.alpha=0.5
        self.frame_idx = 0

    def run(self):
        ret, first_frame = self.cam.read()
        cal_mask = np.zeros_like(first_frame[:, :, 0])
        view_mask = np.zeros_like(first_frame[:, :, 0])
        view_polygon = np.array([[440, 1920], [420, 220], [680, 250], [1080, 480], [1080, 1920]])
        cal_polygon = np.array([[440, 600], [420, 400], [1080, 400], [1080, 600]])
        prv1, prv2, prv3, prv4, prv5 = 0,0,0,0,0
        prn1, prn2, prn3, prn4, prn5 = 0, 0, 0, 0, 0
        ptn1, ptn2, ptn3, ptn4, ptn5 = 0, 0, 0, 0, 0

        pg1 = np.array([[550, 490], [425, 493],[420, 510], [570, 505]]) # RT, LT, LB, RB
        pg2 = np.array([[565, 505], [555, 490], [680, 480], [720, 500]]) # LB, RT, LT, RB
        pg3 = np.array([[680, 490],[690, 480], [800, 470], [800, 495]]) # LB, LT, RT, RB
        pg4 = np.array([[840, 490], [820, 470], [950, 470], [960, 480]]) # LB, LT, LB, RB
        pg5 = np.array([[1080, 480], [970, 480],[960, 470], [1080, 465]]) # RT, LB, LT, RB

        cv.fillConvexPoly(cal_mask, cal_polygon, 1)
        cv.fillConvexPoly(view_mask, view_polygon, 1)

        fourcc = cv.VideoWriter_fourcc(*'XVID')
        out = cv.VideoWriter("output.mp4", fourcc, 30.0, (1080, 1920))

        while (self.cam.isOpened()):
            _ret, frame = self.cam.read()
            if _ret:
                vis = frame.copy()
                cmask = frame.copy()

                mm1, mm2, mm3, mm4, mm5 = 0, 0, 0, 0, 0
                v1, v2, v3, v4, v5 = 0, 0, 0, 0, 0


                frame_gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                frame_gray = cv.bitwise_and(frame_gray, frame_gray, mask=cal_mask)

                vis = cv.bitwise_and(vis, vis, mask=view_mask)
                cv.line(vis,(400, 510),(1080, 475),(0, 0, 255), 5)
                cv.line(vis, (400, 495), (1080, 460), (0, 0, 255), 5)

                cv.fillPoly(cmask, [pg1], (120, 0, 120), cv.LINE_AA)
                cv.fillPoly(cmask, [pg2], (120, 120, 0), cv.LINE_AA)
                cv.fillPoly(cmask, [pg3], (0, 120, 120), cv.LINE_AA)
                cv.fillPoly(cmask, [pg4], (80, 0, 255), cv.LINE_AA)
                cv.fillPoly(cmask, [pg5], (255, 0, 80), cv.LINE_AA)

                draw_str(vis, (30, 40), '1-lane speed: %d km/h' % prv1)
                draw_str(vis, (30, 80), '2-lane speed: %d km/h' % prv2)
                draw_str(vis, (30, 120), '3-lane speed: %d km/h' % prv3)
                draw_str(vis, (30, 160), '4-lane speed: %d km/h' % prv4)
                draw_str(vis, (30, 200), '5-lane speed: %d km/h' % prv5)
                draw_str(vis, (900, 40), 'ptn1: %d' % prn1)
                draw_str(vis, (900, 80), 'ptn2: %d' % prn2)
                draw_str(vis, (900, 120), 'ptn3: %d' % prn3)
                draw_str(vis, (900, 160), 'ptn4: %d' % prn4)
                draw_str(vis, (900, 200), 'ptn5: %d' %prn5)

                if len(self.tracks) > 0:
                    img0, img1 = self.prev_gray, frame_gray
                    p0 = np.float32([tr[-1] for tr in self.tracks]).reshape(-1, 1, 2)
                    p1, _st, _err = cv.calcOpticalFlowPyrLK(img0, img1, p0, None, **lk_params)
                    p0r, _st, _err = cv.calcOpticalFlowPyrLK(img1, img0, p1, None, **lk_params)
                    d = abs(p0-p0r).reshape(-1, 2).max(-1)
                    good = d < 1
                    new_tracks = []
                    for tr, (x, y), good_flag in zip(self.tracks, p1.reshape(-1, 2), good):
                        if not good_flag:
                            continue
                        tr.append((x, y))
                        if len(tr) > self.track_len:
                            del tr[0]
                        new_tracks.append(tr)
                        cv.circle(vis, (x, y), 3, (0, 255, 0), -1)
                    self.tracks = new_tracks

                    ptn1, ptn2, ptn3, ptn4, ptn5 = 0, 0, 0, 0, 0
                    import time
                    start = time.time()  # 시작 시간 저장
                    for idx, tr in enumerate(self.tracks):
                        #print(self.frame_idx, tr)
                        result_pg1 = cv.pointPolygonTest(pg1, tr[0],True)
                        result_pg2 = cv.pointPolygonTest(pg2, tr[0], True)
                        result_pg3 = cv.pointPolygonTest(pg3, tr[0], True)
                        result_pg4 = cv.pointPolygonTest(pg4, tr[0], True)
                        result_pg5 = cv.pointPolygonTest(pg5, tr[0], True)

                        if result_pg1 > 0:
                            ptn1 += 1
                            dif1 = tuple(map(lambda i, j: i - j, tr[0], tr[1]))
                            mm1 += math.sqrt(dif1[0]*dif1[0] + dif1[1]*dif1[1])
                            mmm1 = mm1/ptn1
                            v1 = mmm1*px2m1*fps*ms2kmh
                        if result_pg2 > 0:
                            ptn2 += 1
                            dif2 = tuple(map(lambda i, j: i - j, tr[0], tr[1]))
                            mm2 += math.sqrt(dif2[0] * dif2[0] + dif2[1] * dif2[1])
                            mmm2 = mm2 / ptn2
                            v2 = mmm2 * px2m2 * fps*ms2kmh
                        if result_pg3 > 0:
                            ptn3 += 1
                            dif3 = tuple(map(lambda i, j: i - j, tr[0], tr[1]))
                            mm3 += math.sqrt(dif3[0] * dif3[0] + dif3[1] * dif3[1])
                            mmm3 = mm3 / ptn3
                            v3 = mmm3 * px2m3 * fps*ms2kmh
                        if result_pg4 > 0:
                            ptn4 += 1
                            dif4 = tuple(map(lambda i, j: i - j, tr[0], tr[1]))
                            mm4 += math.sqrt(dif4[0] * dif4[0] + dif4[1] * dif4[1])
                            mmm4 = mm4 / ptn4
                            v4 = mmm4 * px2m4 * fps*ms2kmh
                        if result_pg5 > 0:
                            ptn5 += 1
                            dif5 = tuple(map(lambda i, j: i - j, tr[0], tr[1]))
                            mm5 += math.sqrt(dif5[0] * dif5[0] + dif5[1] * dif5[1])
                            mmm5 = mm5 / ptn5
                            v5 = mmm5 * px2m5 * fps*ms2kmh
                    #print("time :", time.time() - start)  # 현재시각 - 시작시간 = 실행 시간
                    cv.polylines(vis, [np.int32(tr) for tr in self.tracks], False, (0, 0, 255))

                prn1 = ptn1
                prn2 = ptn2
                prn3 = ptn3
                prn4 = ptn4
                prn5 = ptn5

                if self.frame_idx % self.detect_interval == 0:
                    if ptn1 > 5:
                        #print("calc-1")
                        draw_str(vis, (900, 40), 'ptn1: %d' % ptn1)
                        draw_str(vis, (30, 40), '1-lane speed: %d km/h' % v1, color=(0, 0, 255))
                        prv1 = v1
                    if ptn2 > 5:
                        #print("calc-2")
                        draw_str(vis, (900, 80), 'ptn2: %d' % ptn2)
                        draw_str(vis, (30, 80), '2-lane speed: %d km/h' % v2, color=(0, 0, 255))
                        prv2 = v2
                    if ptn3 > 5:
                        #print("calc-3")
                        draw_str(vis, (900, 120), 'ptn3: %d' % ptn3)
                        draw_str(vis, (30, 120), '3-lane speed: %d km/h' % v3, color=(0, 0, 255))
                        prv3 = v3
                    if ptn4 > 5:
                        #print("calc-4")
                        draw_str(vis, (900, 160), 'ptn4: %d' % ptn4)
                        draw_str(vis, (30, 160), '4-lane speed: %d km/h' % v4, color=(0, 0, 255))
                        prv4 = v4
                    if ptn5 > 5:
                        #print("calc-5")
                        draw_str(vis, (900, 200), 'ptn5: %d' % ptn5)
                        draw_str(vis, (30, 200), '5-lane speed: %d km/h' % v5, color=(0, 0, 255))
                        prv5 = v5


                    mask = np.zeros_like(frame_gray)
                    mask[:] = 255
                    for x, y in [np.int32(tr[-1]) for tr in self.tracks]:
                        cv.circle(mask, (x, y), 3, 0, -1)
                    p = cv.goodFeaturesToTrack(frame_gray, mask = mask, **feature_params)
                    if p is not None:
                        for x, y in np.float32(p).reshape(-1, 2):
                            self.tracks.append([(x, y)])#


                self.frame_idx += 1
                self.prev_gray = frame_gray
                cv.addWeighted(cmask, self.alpha, vis, 1 - self.alpha, 0, vis)
                out.write(vis)
                #cv.imshow('lk_track', vis)
                #cv.waitKey(0)
                if cv.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                break
        out.release()
        self.cam.release()
        cv.destroyAllWindows()

def main():
    import sys
    try:
        video_src = sys.argv[1]
    except:
        video_src = 0
    app = App(video_src)
    app.run()
    print('Done')


if __name__ == '__main__':
    print(__doc__)
    main()
