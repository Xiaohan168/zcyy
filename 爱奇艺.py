# -*- coding: utf-8 -*-
# by @嗷呜
import random
import sys
from base64 import b64encode, b64decode
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlencode
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.did = self.random_str(32)
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    rhost = 'https://www.iqiyi.com'

    hhost='https://mesh.if.iqiyi.com'

    dhost='https://miniapp.iqiyi.com'

    headers = {
        'Origin': rhost,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Referer': f'{rhost}/',
    }

    def homeContent(self, filter):
        result = {}
        cateManual = {
            "全部": "1009",
            "电影": "1",
            "剧集": "2",
            "综艺": "6",
            "动漫": "4",
            "儿童": "15",
            "微剧": "35",
            "纪录片": "3"
        }
        classes = []
        filters = {}
        for k in cateManual:
            classes.append({
                'type_name': k,
                'type_id': cateManual[k]
            })
        with ThreadPoolExecutor(max_workers=len(classes)) as executor:
            results = executor.map(self.getf, classes)
            for id, ft in results:
                if len(ft):filters[id] = ft
        result['class'] = classes
        result['filters'] = filters
        return result

    def homeVideoContent(self):
        data=self.fetch(f'{self.hhost}/portal/lw/v5/channel/recommend?v=13.014.21150', headers=self.headers).json()
        vlist = []
        for i in data['items'][1:]:
            for j in i['video'][0]['data']:
                id = j.get('firstId')
                pic=j.get('prevue',{}).get('image_url') or j.get('album_image_url_hover')
                if id and pic:
                    pu=j.get('prevue',{}).get('page_url') or j.get('page_url').split('?')[0]
                    id = f'{id}@{self.e64(pu)}'
                    vlist.append({
                        'vod_id': id,
                        'vod_name': j.get('display_name'),
                        'vod_pic': pic,
                        'vod_year': j.get('sns_score'),
                        'vod_remarks': j.get('dq_updatestatus') or j.get('rank_prefix')
                    })
        return {'list':vlist}

    def categoryContent(self, tid, pg, filter, extend):
        if pg == "1":
            self.sid = ''
        new_data = {'mode':'24'}
        for key, value in extend.items():
            if value:
                key_value_pairs = self.d64(value).split(',')
                for pair in key_value_pairs:
                    k, v = pair.split('=')
                    if k in new_data:
                        new_data[k] += "," + v
                    else:
                        new_data[k] = v
        path=f'/portal/lw/videolib/data?uid=&passport_id=&ret_num=60&version=13.014.21150&device_id={self.did}&channel_id={tid}&page_id={pg}&session={self.sid}&os=&conduit_id=&vip=0&auth&recent_selected_tag=&ad=%5B%7B%22lm%22:%225%22,%22ai%22:%225%22,%22fp%22:%226%22,%22sei%22:%22Sa867aa9d326e2bd8654d8c2a8636055e%22,%22position%22:%22library%22%7D%5D&adExt=%7B%22r%22:%221.2.1-ares6-pure%22%7D&dfp=a12f96215b2f7842a98c082799ca0c3d9236be00946701b106829754d8ece3aaf8&filter={urlencode(new_data)}'
        data=self.fetch(f'{self.hhost}{path}', headers=self.headers).json()
        self.sid = data['session']
        videos = []
        for i in data['data']:
            id = i.get('firstId') or i.get('tv_id')
            if not id:
                id=i.get('play_url').split(';')[0].split('=')[-1]
            if id and not i.get('h'):
                id=f'{id}@{self.e64(i.get("page_url"))}'
                videos.append({
                    'vod_id': id,
                    'vod_name': i.get('display_name'),
                    'vod_pic': i.get('album_image_url_hover'),
                    'vod_year': i.get('sns_score'),
                    'vod_remarks': i.get('dq_updatestatus') or i.get('pay_mark')
                })
        result = {}
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        ids = ids[0].split('@')
        ids[-1] = self.d64(ids[-1])
        data = self.fetch(f'{self.dhost}/h5/mina/baidu/play/body/v1/{ids[0]}/', headers=self.headers).json()
        v=data['data']['playInfo']
        vod = {
            'vod_name': v.get('albumName'),
            'type_name': v.get('tags'),
            'vod_year': v.get('albumYear'),
            'vod_remarks': v.get('updateStrategy'),
            'vod_actor': v.get('mainActors'),
            'vod_director': v.get('directors'),
            'vod_content': v.get('albumDesc'),
            'vod_play_from': '爱奇艺',
            'vod_play_url': ''
        }
        if data.get('data') and data['data'].get('videoList') and data['data']['videoList'].get('videos'):
            purl=[f'{i["shortTitle"]}${i["pageUrl"]}' for i in data['data']['videoList']['videos']]
            pg=data['data']['videoList'].get('totalPages')
            if pg and pg > 1:
                id = v['albumId']
                pages = list(range(2, pg + 1))
                page_results = {}
                with ThreadPoolExecutor(max_workers=10) as executor:
                    future_to_page = {
                        executor.submit(self.fetch_page_data, page, id): page
                        for page in pages
                    }
                    for future in as_completed(future_to_page):
                        page = future_to_page[future]
                        try:
                            result = future.result()
                            page_results[page] = result
                        except Exception as e:
                            print(f"Error fetching page {page}: {e}")
                for page in sorted(page_results.keys()):
                    purl.extend(page_results[page])
            vod['vod_play_url'] = '#'.join(purl)
        else:
            vdata=self.fetch(f'{self.dhost}/h5/mina/baidu/play/head/v1/{ids[0]}/', headers=self.headers).json()
            v=vdata['data']['playInfo']
            vod = {
                'vod_name': v.get('shortTitle'),
                'type_name': v.get('channelName'),
                'vod_year': v.get('year'),
                'vod_remarks': v.get('focus'),
                'vod_actor': v.get('mainActors'),
                'vod_director': v.get('directors'),
                'vod_content': v.get('desc'),
                'vod_play_from': '爱奇艺',
                'vod_play_url': f'{v.get("shortTitle")}${ids[-1]}'
            }
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.fetch(f'{self.hhost}/portal/lw/search/homePageV3?key={key}&current_page={pg}&mode=1&source=input&suggest=&version=13.014.21150&pageNum={pg}&pageSize=25&pu=&u={self.did}&scale=150&token=&userVip=0&conduit=&vipType=-1&os=&osShortName=win10&dataType=&appMode=', headers=self.headers).json()
        videos = []
        vdata=data['data']['templates']
        for i in data['data']['templates']:
            if i.get('intentAlbumInfos'):
                vdata=[{'albumInfo': c} for c in i['intentAlbumInfos']]+vdata

        for i in vdata:
            if i.get('albumInfo') and (i['albumInfo'].get('playQipuId','') or i['albumInfo'].get('qipuId')) and i['albumInfo'].get('pageUrl'):
                b=i['albumInfo']
                id=f"{(b.get('playQipuId','') or b.get('qipuId'))}@{self.e64(b.get('pageUrl'))}"
                videos.append({
                    'vod_id': id,
                    'vod_name': b.get('title'),
                    'vod_pic': b.get('img'),
                    'vod_year': (b.get('year',{}) or {}).get('value'),
                    'vod_remarks': b.get('subscriptContent') or b.get('channel') or b.get('vipTips')
                })
        return {'list':videos,'page':pg}

    def playerContent(self, flag, id, vipFlags):
        return  {'jx':1,'parse': 1, 'url': id, 'header': ''}

    def localProxy(self, param):
        pass

    def fetch_page_data(self, page, id):
        try:
            url = f'{self.dhost}/h5/mina/avlist/{page}/{id}/'
            data = self.fetch(url, headers=self.headers).json()
            return [f'{i["shortTitle"]}${i["pageUrl"]}' for i in data['data']['videoList']['videos']]
        except:
            return []

    def getf(self,body):
        data=self.fetch(f'{self.hhost}/portal/lw/videolib/tag?channel_id={body["type_id"]}&tagAdd=&selected_tag_name=&version=13.014.21150&device={self.did}&uid=', headers=self.headers).json()
        ft = []
        # for i in data[:-1]:
        for i in data:
            try:
                value_array = [{"n": value['text'], "v": self.e64(value['tag_param'])} for value in i['tags'] if
                               value.get('tag_param')]
                ft.append({"key": i['group'], "name": i['group'], "value": value_array})
            except:
                print(i)
        return (body['type_id'], ft)

    def e64(self, text):
        try:
            text_bytes = text.encode('utf-8')
            encoded_bytes = b64encode(text_bytes)
            return encoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64编码错误: {str(e)}")
            return ""

    def d64(self,encoded_text: str):
        try:
            encoded_bytes = encoded_text.encode('utf-8')
            decoded_bytes = b64decode(encoded_bytes)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            print(f"Base64解码错误: {str(e)}")
            return ""

    def random_str(self,length=16):
        hex_chars = '0123456789abcdef'
        return ''.join(random.choice(hex_chars) for _ in range(length))
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  get(url, headers=headers, params=params, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"请求失败: {url}, 错误: {e}")
            return None

    def homeContent(self, filter):
        result = {}
        classes = []
        for k, v in self.channels.items():
            classes.append({
                'type_id': k,
                'type_name': v['name']
            })
        result['class'] = classes
        if filter:
            result['filters'] = self.filters
        return result

    def homeVideoContent(self):
        result = {}
        videos = []
        try:
            for channel_id in ['2', '1', '3', '4']:
                url = f'{self.pcwApi}/search/recommend/list'
                params = {
                    'channel_id': self.channels[channel_id]['channel_id'],
                    'data_type': '1',
                    'mode': '11',
                    'page_id': '1',
                    'ret_num': '12',
                    'session': ''
                }
                response = self.fetch(url, params=params)
                if response:
                    data = response.json()
                    if data.get('code') == 'A00000' and data.get('data', {}).get('list'):
                        for item in data['data']['list'][:6]:
                            videos.append(self._parseVideoItem(item))
                if len(videos) >= 24:
                    break
        except Exception as e:
            print(f"获取首页视频失败: {e}")
        result['list'] = videos
        return result

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        try:
            channel_info = self.channels.get(tid, {})
            channel_id = channel_info.get('channel_id', '2')
            
            mode = extend.get('mode', '24') if extend else '24'
            
            url = f'{self.pcwApi}/search/recommend/list'
            params = {
                'channel_id': channel_id,
                'data_type': '1',
                'mode': mode,
                'page_id': str(pg),
                'ret_num': '48',
                'session': ''
            }
            
            response = self.fetch(url, params=params)
            if response:
                data = response.json()
                if data.get('code') == 'A00000' and data.get('data', {}).get('list'):
                    for item in data['data']['list']:
                        videos.append(self._parseVideoItem(item))
                    
                    has_next = data['data'].get('has_next', 0)
                    pagecount = pg + 1 if has_next else pg
                    total = len(videos) * pg
                else:
                    pagecount = pg
                    total = len(videos)
            else:
                pagecount = pg
                total = len(videos)
        except Exception as e:
            print(f"获取分类内容失败: {e}")
            pagecount = pg
            total = len(videos)
        
        result['list'] = videos
        result['page'] = pg
        result['pagecount'] = pagecount
        result['limit'] = 48
        result['total'] = total
        return result

    def detailContent(self, ids):
        result = {}
        try:
            video_id = ids[0]
            album_id = video_id.split('_')[0] if '_' in video_id else video_id
            
            # 获取剧集列表
            url = f'{self.pcwApi}/albums/album/avlistinfo'
            params = {
                'aid': album_id,
                'page': '1',
                'size': '30'
            }
            response = self.fetch(url, params=params)
            
            episodes = []
            first_ep = {}
            album_name = ''
            album_pic = ''
            album_desc = ''
            directors = []
            actors = []
            
            if response:
                data = response.json()
                if data.get('code') == 'A00000' and data.get('data', {}).get('epsodelist'):
                    album_data = data['data']
                    episodes = album_data['epsodelist']
                    first_ep = episodes[0] if episodes else {}
            
            # 获取专辑详细信息（用于获取正确的剧名、导演、演员、简介）
            # 电视剧通过avlistinfo获取tvId后再查baseinfo，电影直接用albumId查
            tv_id = first_ep.get('tvId') if first_ep else None
            if not tv_id:
                tv_id = album_id
            
            if tv_id:
                base_url = f'{self.pcwApi}/video/video/baseinfo/{tv_id}'
                base_response = self.fetch(base_url)
                if base_response:
                    base_data = base_response.json()
                    if base_data.get('code') == 'A00000' and base_data.get('data'):
                        base_info = base_data['data']
                        album_name = base_info.get('albumName', '')
                        album_pic = base_info.get('albumImageUrl', '')
                        album_desc = base_info.get('description', '')
                        people = base_info.get('people', {})
                        if people:
                            director_list = people.get('director', [])
                            directors = [d.get('name', '') for d in director_list if d.get('name')]
                            actor_list = people.get('main_charactor', [])
                            actors = [a.get('name', '') for a in actor_list if a.get('name')]
                        # 电影可能没有avlistinfo数据，用baseinfo补充播放链接
                        if not episodes and base_info.get('playUrl'):
                            episodes = [{
                                'shortTitle': base_info.get('name', album_name),
                                'name': base_info.get('name', album_name),
                                'playUrl': base_info.get('playUrl', ''),
                                'imageUrl': base_info.get('imageUrl', ''),
                                'duration': base_info.get('duration', ''),
                                'description': base_info.get('description', '')
                            }]
            
            # 如果baseinfo获取失败，从avlistinfo补充
            if not album_name and first_ep:
                album_name = self._extractAlbumName(first_ep.get('name', ''), first_ep.get('shortTitle', ''))
            if not album_pic and first_ep:
                album_pic = first_ep.get('imageUrl', '')
            if not album_desc and first_ep:
                album_desc = first_ep.get('description', '')
            if not directors and first_ep and first_ep.get('people'):
                director_list = first_ep['people'].get('director', [])
                directors = [d.get('name', '') for d in director_list if d.get('name')]
            if not actors and first_ep and first_ep.get('people'):
                actor_list = first_ep['people'].get('main_charactor', [])
                actors = [a.get('name', '') for a in actor_list if a.get('name')]
            
            # 构建播放列表
            play_from = ['爱奇艺']
            play_urls = []
            
            for ep in episodes:
                ep_name = ep.get('shortTitle', ep.get('name', ''))
                ep_url = ep.get('playUrl', '')
                if ep_url:
                    # 转为移动端URL，提升兼容性
                    ep_url = ep_url.replace('http://www.iqiyi.com/', 'https://m.iqiyi.com/')
                    ep_url = ep_url.replace('https://www.iqiyi.com/', 'https://m.iqiyi.com/')
                    play_urls.append(f"{ep_name}${ep_url}")
            
            play_url = '#'.join(play_urls)
            
            # 清理简介中的多余换行和空格
            album_desc = album_desc.replace('\n\n', '\n').strip() if album_desc else ''
            
            vod = {
                "vod_id": video_id,
                "vod_name": album_name,
                "vod_pic": album_pic,
                "vod_remarks": f"共{len(episodes)}集" if len(episodes) > 1 else (first_ep.get('duration', '') or '电影'),
                "vod_actor": ' '.join(actors[:8]),
                "vod_director": ' '.join(directors[:3]),
                "vod_content": album_desc,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join([play_url])
            }
            result['list'] = [vod]
        except Exception as e:
            print(f"获取详情失败: {e}")
            result['list'] = []
        return result

    def _extractAlbumName(self, name, short_title):
        """智能提取剧名"""
        text = name or short_title or ''
        if not text:
            return ''
        # 匹配 "剧名第N集" 格式
        match = re.match(r'^(.*?)(第\d+集|第[一二三四五六七八九十百]+集|预告|片花|花絮|特辑)', text)
        if match:
            name = match.group(1).strip()
            if name:
                return name
        # 如果是 "第N集" 开头，无法提取，返回原值
        if text.startswith('第'):
            return text
        return text

    def searchContent(self, key, quick, pg=1):
        result = {}
        videos = []
        try:
            url = self.searchApi
            params = {
                'if': 'html5',
                'key': key,
                'pageNum': str(pg),
                'pageSize': '25'
            }
            response = self.fetch(url, params=params)
            if response:
                data = response.json()
                if data.get('data', {}).get('docinfos'):
                    for item in data['data']['docinfos']:
                        album_info = item.get('albumDocInfo', {})
                        if album_info and album_info.get('albumId'):
                            # 过滤掉无效结果
                            title = album_info.get('albumTitle', '')
                            if not title:
                                continue
                            videos.append({
                                "vod_id": str(album_info.get('albumId', '')),
                                "vod_name": title,
                                "vod_pic": album_info.get('albumVImage', '') or album_info.get('albumImg', ''),
                                "vod_remarks": album_info.get('tvFocus', '') or f"{album_info.get('itemTotalNumber', 0)}集"
                            })
                    result = {
                        'list': videos,
                        'page': pg,
                        'pagecount': 999,
                        'limit': 25,
                        'total': len(videos)
                    }
        except Exception as e:
            print(f"搜索失败: {e}")
        if not result:
            result = {'list': videos, 'page': pg, 'pagecount': pg, 'limit': 25, 'total': len(videos)}
        return result

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        result = {}
        try:
            play_url = id
            # 统一转为移动端URL，提升OK影视兼容性
            if play_url and play_url.startswith('http'):
                play_url = play_url.replace('http://www.iqiyi.com/', 'https://m.iqiyi.com/')
                play_url = play_url.replace('https://www.iqiyi.com/', 'https://m.iqiyi.com/')
            
            if self.isVideoFormat(play_url):
                result["parse"] = 0
                result["url"] = play_url
            else:
                result["parse"] = 1
                result["url"] = play_url
                result["jx"] = "1"
            
            result["header"] = {
                "User-Agent": self.userAgent,
                "Referer": "https://m.iqiyi.com/",
                "Origin": "https://m.iqiyi.com"
            }
        except Exception as e:
            print(f"获取播放内容失败: {e}")
        return result

    def isVideoFormat(self, url):
        video_formats = ['.mp4', '.m3u8', '.ts', '.mkv', '.avi', '.flv', '.webm']
        if url and url.startswith('http'):
            for fmt in video_formats:
                if url.lower().find(fmt) > -1:
                    return True
        return False

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def _parseVideoItem(self, item):
        return {
            "vod_id": str(item.get('albumId', '')),
            "vod_name": item.get('name', ''),
            "vod_pic": item.get('imageUrl', ''),
            "vod_remarks": item.get('focus', '') or f"更新至{item.get('latestOrder', 0)}集",
            "vod_year": str(item.get('period', ''))[:4] if item.get('period') else '',
            "vod_area": ','.join(item.get('categories', []))
        }

if __name__ == '__main__':
    spider = Spider()
    print(json.dumps(spider.homeContent(True), ensure_ascii=False, indent=2))
