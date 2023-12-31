import argparse
import time
from pathlib import Path

import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized, TracedModel


def detect(source,weights,device,img_size,iou_thres,conf_thres):

    webcam = int(source)

    set_logging()
    device = select_device(device)
    half = device.type != 'cpu'
    model = attempt_load(weights,map_location=device)
    stride = int(model.stride.max())
    imgsz= check_img_size(img_size,s=stride)

    if half:
        model.half()



    if webcam == 0:
        view_img = check_imshow()
        cudnn.benchmark = True
        dataset = LoadStreams(source,img_size = imgsz,stride=stride)


        names = model.module.names if hasattr(model,'module') else model.names
        colors = [[random.randint(0,255) for _ in range(3)]for _ in names]

        if device.type != 'cpu':
            model(torch.zeros(3,3,imgsz,imgsz).to(device).type_as(next(model.parameters())))

        old_img_w = old_img_h = img_size
        old_img_b = 1

        t0 = time.perf_counter()

        for path,img,im0s,vid_cap in dataset:
            img = torch.from_numpy(img).to(device)
            img = img.half() if half else img.float()
            img /=255.0
            if img.ndimension() == 3:
                img = img.unsqueeze(0)


            if device.type != 'cpu' and (old_img_b !=img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]):
                old_img_b = img.shape[0]
                old_img_h = img.shape[2]
                old_img_w = img.shape[3]

            t1 = time_synchronized()
            with torch.no_grad():
                pred = model(img)[0]
            t2 = time_synchronized()



            pred = non_max_suppression(pred,conf_thres,iou_thres)
            t3 = time_synchronized()

            for i,det in enumerate(pred):
                if webcam == 0:
                    p,s,im0,frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count

                p = Path(p)

                gn = torch.tensor(im0.shape)[[1,0,1,0]]

                if len(det):

                    det[:, :4] = scale_coords(img.shape[2:], det[:,:4],im0.shape)


                    for c in det[:,-1].unique():
                        n = (det[:,-1] == c).sum()
                        s+= f"{n} {names[int(c)]}{'s'*(n>1)}, "

                    for *xyxy,conf,cls in reversed(det):

                        label = f'{names[int(cls)]} {conf:.2f}'
                        plot_one_box(xyxy,im0,label=label, color=colors[int(cls)],line_thickness=1)

            cv2.imshow(str(p),im0)


    


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    print(device)

    with torch.no_grad():
        detect("0","best(2).pt",device,img_size=640,iou_thres=0.45,conf_thres=0.60)