# -*- coding: utf-8 -*-

"""
# === 思路 ===
# 核心：每次落稳之后截图，根据截图算出棋子的坐标和下一个块顶面的中点坐标，
#      根据两个点的距离乘以一个时间系数获得长按的时间
# 识别棋子：靠棋子的颜色来识别位置，通过截图发现最下面一行大概是一条
           直线，就从上往下一行一行遍历，比较颜色（颜色用了一个区间来比较）
           找到最下面的那一行的所有点，然后求个中点，求好之后再让 Y 轴坐标
           减小棋子底盘的一半高度从而得到中心点的坐标
# 识别棋盘：靠底色和方块的色差来做，从分数之下的位置开始，一行一行扫描，
           由于圆形的块最顶上是一条线，方形的上面大概是一个点，所以就
           用类似识别棋子的做法多识别了几个点求中点，这时候得到了块中点的 X
           轴坐标，这时候假设现在棋子在当前块的中心，根据一个通过截图获取的
           固定的角度来推出中点的 Y 坐标
# 最后：根据两点的坐标算距离乘以系数来获取长按时间（似乎可以直接用 X 轴距离）
"""
import os
import shutil #文件及文件夹操作库
import time
import math
import random
import json
from PIL import Image, ImageDraw
import wda #facebook-wda库的python版


with open('config.json', 'r') as f:
    config = json.load(f)


# Magic Number，不设置可能无法正常执行，请根据具体截图从上到下按需设置
under_game_score_y = config['under_game_score_y']
# 长按的时间系数，请自己根据实际情况调节
press_coefficient = config['press_coefficient']
# 二分之一的棋子底座高度，可能要调节
piece_base_height_1_2 = config['piece_base_height_1_2']
# 棋子的宽度，比截图中量到的稍微大一点比较安全，可能要调节
piece_body_width = config['piece_body_width']
time_coefficient = config['press_coefficient']

# 模拟按压的起始点坐标，需要自动重复游戏请设置成“再来一局”的坐标
swipe = config.get('swipe', {
    "x1": 320,
    "y1": 410,
    "x2": 320,
    "y2": 410
    })

c = wda.Client()
s = c.session()

#设置截屏目录
screenshot_backup_dir = 'screenshot_backups/'
if not os.path.isdir(screenshot_backup_dir):
    os.mkdir(screenshot_backup_dir)


def pull_screenshot():
    c.screenshot('1.png')


def jump(distance):
    press_time = distance * time_coefficient / 1000
    print('press time: {}'.format(press_time))
    s.tap_hold(random.uniform(0, 320), random.uniform(64, 320), press_time)


def backup_screenshot(ts):
    """
    为了方便失败的时候 debug
    """
    if not os.path.isdir(screenshot_backup_dir):
        os.mkdir(screenshot_backup_dir)
    shutil.copy('1.png', '{}{}.png'.format(screenshot_backup_dir, ts))


def save_debug_creenshot(ts, im, piece_x, piece_y, board_x, board_y):
    draw = ImageDraw.Draw(im)
    # 对debug图片加上详细的注释
    draw.line((piece_x, piece_y) + (board_x, board_y), fill=2, width=3)
    draw.line((piece_x, 0, piece_x, im.size[1]), fill=(255, 0, 0))
    draw.line((0, piece_y, im.size[0], piece_y), fill=(255, 0, 0))
    draw.line((board_x, 0, board_x, im.size[1]), fill=(0, 0, 255))
    draw.line((0, board_y, im.size[0], board_y), fill=(0, 0, 255))
    draw.ellipse(
        (piece_x - 10, piece_y - 10, piece_x + 10, piece_y + 10),
        fill=(255, 0, 0))
    draw.ellipse(
        (board_x - 10, board_y - 10, board_x + 10, board_y + 10),
        fill=(0, 0, 255))
    del draw
    im.save('{}{}_d.png'.format(screenshot_backup_dir, ts))


def set_button_position(im):
    """
    将swipe设置为 `再来一局` 按钮的位置
    """
    global swipe_x1, swipe_y1, swipe_x2, swipe_y2
    w, h = im.size
    left = w / 2
    top = 1003 * (h / 1280.0) + 10
    swipe_x1, swipe_y1, swipe_x2, swipe_y2 = left, top, left, top


def find_piece_and_board(im):
    #im是一张图片
    w, h = im.size

    print("size: {}, {}".format(w, h))

    piece_x_sum = piece_x_c = piece_y_max = 0
    board_x = board_y = 0
    scan_x_border = int(w / 8)  # 扫描棋子时的左右边界
    scan_start_y = 0  # 扫描的起始 y 坐标
    im_pixel = im.load() #把图片读成像素

    # 确定起始扫描高度y，左上角为0，0
    # 以 50px 步长，尝试探测 scan_start_y，从分数显示位以下开始扫描
    # 步长50是为了加速，只是为了一个起始扫描y值而已
    for i in range(under_game_score_y, h, 50):
        last_pixel = im_pixel[0, i]
        for j in range(1, w):
            pixel = im_pixel[j, i]

            # 不是纯色的线，则记录scan_start_y的值，准备跳出循环
            # 即从上向下扫描至第一个形状
            if pixel != last_pixel:
                scan_start_y = i - 50
                break

        if scan_start_y:
            break

    print("scan_start_y: ", scan_start_y)

    # 从 scan_start_y 开始往下扫描，棋子应位于屏幕上半部分，这里暂定不超过 2/3
    for i in range(scan_start_y, int(h * 2 / 3)):
        # 横坐标方面也减少了一部分扫描开销，根据前述设置，从1/8宽度开始
        for j in range(scan_x_border, w - scan_x_border):
            pixel = im_pixel[j, i]
            # 根据棋子的最低行的颜色判断，找最后一行那些点的平均值，这个颜
            # 色这样应该 OK，暂时不提出来
            # 分别为RGB的颜色，\为代码连续隔断
            if (50 < pixel[0] < 60) \
                    and (53 < pixel[1] < 63) \
                    and (95 < pixel[2] < 110):
                #由于棋子是个等腰形，所以这里是把所有的符合颜色的x值都汇总了，期平均值应与一行
                #汇总平均值是一样的，避免两次循环
                piece_x_sum += j
                piece_x_c += 1
                #获取到最后一行符合颜色标准
                piece_y_max = max(i, piece_y_max)
    #判断有没有抓到棋子
    if not all((piece_x_sum, piece_x_c)):
        return 0, 0, 0, 0
    #取所有的X平均值，获得x中央值
    piece_x = piece_x_sum / piece_x_c
    #以最后一行的y向上移动20，（没有太大意义，只是为了假设一个中点，如不移也可以）
    piece_y = piece_y_max - piece_base_height_1_2  # 上移棋子底盘高度的一半

    #扫棋盘，从1/3开始扫，其实应该从前面的scan_start_y开始扫更好，扫到棋子脚
    #for i in range(int(h / 3), int(h * 2 / 3)):
    #先假设一个board_y_tmp用于以后纠偏用
    board_y_tmp = 0
    for i in range(int(h / 3), piece_y):
        #获取得一个点
        last_pixel = im_pixel[40, i]
        #初始为0，并为跳出设置
        if board_x:# or board_y:
            break
        board_x_sum = 0
        board_x_c = 0
        #扫描从0到屏宽全扫【个人认为应从右向左扫】
        for j in range(w):
            pixel = im_pixel[j, i]
            # 修掉脑袋比下一个小格子还高的情况的 bug
            # 也就是如果j的值与棋子的x是左右各半身的话，我们假设这个不是形状点
            # 这其实有个bug，因为很有可能正方与圆的顶落在头上，所以应当根据后续判断
            # 即如果下面有超过棋子x的，再根据x和w-x是不存在，找到最大的，然后求中
            if abs(j - piece_x) < piece_body_width:
                continue

            # 修掉圆顶的时候一条线导致的小 bug，这个颜色判断应该 OK，暂时不提出来
            if abs(pixel[0] - last_pixel[0]) \
                    + abs(pixel[1] - last_pixel[1]) \
                    + abs(pixel[2] - last_pixel[2]) > 10:
                board_x_sum += j
                board_x_c += 1
                board_y_tmp = max(i,board_y_tmp)
        #搜到最顶行就结束了
        if board_x_sum:
            board_x = board_x_sum / board_x_c

    board_y_tmp = board_y_tmp


    # 按实际的角度来算，找到接近下一个 board 中心的坐标 这里的角度应该
    # 是 30°,值应该是 tan 30°, math.sqrt(3) / 3
    # 但实际上并不是所有的都是30度
    board_y_key = piece_y - abs(board_x - piece_x) * math.sqrt(3) / 3

    #需要根据差距大小设定偏离幅度
    if abs((board_y_tmp-board_y_key)) < 20.0:
        board_y = board_y_key
    else:
        board_y = random.uniform(board_y_key,board_y_key+(board_y_tmp-board_y_key)/3)

    print('最小%s,最大%s,取值%s'%(board_y_key,(board_y_key+(board_y_tmp-board_y_key)/3),board_y))



    if not all((board_x, board_y)):
        return 0, 0, 0, 0

    return piece_x, piece_y, board_x, board_y


def main():
    while True:
        pull_screenshot()
        im = Image.open("./1.png")  #open是可写的，load是只读的

        # 获取棋子和 board 的位置
        piece_x, piece_y, board_x, board_y = find_piece_and_board(im)
        ts = int(time.time())
        print(ts, piece_x, piece_y, board_x, board_y)
        if piece_x == 0:
            return

        set_button_position(im)
        distance = math.sqrt(
            (board_x - piece_x) ** 2 + (board_y - piece_y) ** 2)
        jump(distance)

        save_debug_creenshot(ts, im, piece_x, piece_y, board_x, board_y)
        backup_screenshot(ts)
        # 为了保证截图的时候应落稳了，多延迟一会儿，随机值防 ban
        time.sleep(random.uniform(1, 2))


if __name__ == '__main__':
    main()
