import sys
import json
import random
import time
from datetime import datetime, timedelta

from mysports.original_json import no_free_data, host
from mysports.sports import *
from path_plan.plan import path_plan, get_school_location


def no_free_run(userid: str, ses, extra_pn=1, school="", rg=(2, 4), debug=False):
    data = json.dumps({"initLocation": "121.889662,30.895456", "type": "1", "userid": userid})
    res = ses.get(host + '/api/run/runPage', params={'sign': get_md5_code(data), 'data': data.encode('ascii')})
    if res.json()['code'] == 404:
        #print('<NoFreeRunModule>: 体育锻炼接口返回 JSON：', res.json()['msg'])
        return
    resj = res.json()['data']
    #print('<NoFreeRunModule>: 体育锻炼接口返回 JSON：', resj)

    # red, green
    red, green = rg

    school_location = get_school_location(school)
    if debug:
        print('school:' + str(school) + ' ' + 'location:' + str(school_location))
    # 处理节点
    possible_bNode = [item for item in resj['ibeacon'] if haversine(item['position'], school_location)['km'] < 60]
    possible_tNode = [item for item in resj['gpsinfo'] if haversine(item, school_location)['km'] < 60]

    no_free_data['bNode'] = possible_bNode[:red]
    no_free_data['tNode'] = possible_tNode[:green]
    #print('possible_bNode：', possible_bNode)
    #print('possible_tNode：', possible_tNode)
    if debug:
        print('bNode to use:' + str(no_free_data['bNode']['position']))
        print('tNode to use:' + str(no_free_data['tNode']))
    try:
        position_info = no_free_data['bNode'][0]['position']
    except:
        position_info = no_free_data['tNode'][0]
    start_point = gps_point(float(position_info['latitude']), float(position_info['longitude']))

    # pass_by_ps : List[gps_point]
    pass_by_ps = gps_point_list([start_point.zouzou(strip=0.003) for _ in range(extra_pn)])

    # reformat bnode, tnode ;  collect passby points
    for node in no_free_data['bNode']:
        pos = node['position']
        pos['latitude'] = float(pos['latitude'])
        pos['longitude'] = float(pos['longitude'])
        pos['speed'] = 0.0
        node['position'] = pos

        pass_by_ps.append(gps_point(pos['latitude'], pos['longitude']))

    for pos in no_free_data['tNode']:
        pos['latitude'] = float(pos['latitude'])
        pos['longitude'] = float(pos['longitude'])
        pos['speed'] = 0.0

        pass_by_ps.append(gps_point(pos['latitude'], pos['longitude']))

    # path plan
    plan = path_plan(pass_by_ps)
    dis = max(plan['distance'], 2.0)
    path = plan['path']

    # reformat path
    tmp = []
    for p in path:
        tmp.append({'latitude': p['lat'], 'longitude': p['lng']})
    path = tmp

    # gen speed, duration, speed...
    speed = random.randint(300, 500)  # seconds per km
    duration = dis * speed  # seconds

    # to 'minutes'seconds'microseconds'
    speed = "%s'%s''" % (speed // 60, speed - speed // 60 * 60)
    startTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # peisu = 1000 / (bupin * bufu)
    bupin = random.uniform(120, 140)

    # construct post data
    no_free_data['endTime'] = (datetime.now() + timedelta(seconds=duration)).strftime("%Y-%m-%d %H:%M:%S")
    no_free_data['startTime'] = startTime
    no_free_data['userid'] = userid
    no_free_data['runPageId'] = resj['runPageId']
    no_free_data['real'] = str(dis * 1000)
    no_free_data['duration'] = str(duration)
    no_free_data['speed'] = speed
    no_free_data['track'] = path
    no_free_data['buPin'] = '%.1f' % bupin
    no_free_data['busu'] = "2098"
    #RunTime = timedelta(seconds=duration)
    if not debug:
        #print('Running Finished %s m til %s' % (str(int(dis)*1000), no_free_data['endTime']))
        print('Running Finished  til %s' % no_free_data['endTime'])
    xs = json.dumps(no_free_data)
    process_bar = ShowProcess((int(duration)), 'DONE!')
    for i in range(int(duration)):
        process_bar.show_process()
        time.sleep(1)
    r = ses.post(host + '/api/run/saveRunV2', data={'sign': get_md5_code(xs), 'data': xs.encode('ascii')})
    #print(r.content.decode('utf-8'))
    return dis

class ShowProcess():
    """
    显示处理进度的类
    调用该类相关函数即可实现处理进度的显示
    """
    i = 0 # 当前的处理进度
    max_steps = 0 # 总共需要处理的次数
    max_arrow = 38 #进度条的长度
    infoDone = 'done'

    # 初始化函数，需要知道总共的处理次数
    def __init__(self, max_steps, infoDone = 'Done'):
        self.max_steps = max_steps
        self.i = 0
        self.infoDone = infoDone

    # 显示函数，根据当前的处理进度i显示进度
    def show_process(self, i=None):
        if i is not None:
            self.i = i
        else:
            self.i += 1
        num_arrow = int(self.i * self.max_arrow / self.max_steps) #计算显示多少个'>'
        num_line = self.max_arrow - num_arrow #计算显示多少个'-'
        percent = self.i * 100.0 / self.max_steps #计算完成进度，格式为xx.xx%
        process_bar = '[' + '#' * num_arrow + '-' * num_line + ']'\
                      +  "%.2f%%" %percent+ '\r' #带输出的字符串，'\r'表示不换行回到最左边
        sys.stdout.write(process_bar) #这两句打印字符到终端
        sys.stdout.flush()
        if self.i >= self.max_steps:
            self.close()

    def close(self):
        print('')
        print(self.infoDone)
        self.i = 0
