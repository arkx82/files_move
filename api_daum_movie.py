# -*- coding: UTF-8 -*-
# SJVA, Plex SJ Daum Agent, shell 공용
import os
import sys
import requests, re, json, time
import traceback, unicodedata
from datetime import datetime
import lxml
from lxml import html
from framework import SystemModelSetting, py_urllib, app, py_unicode
from framework.util import Util
from system import SystemLogicTrans
from system.logic_site import SystemLogicSite

from framework import logger
from .plugin import logger, package_name
#from lib_metadata import SiteNaverMovie, SiteTmdbMovie, SiteWatchaMovie, SiteUtil, SiteDaumMovie, SiteTvingMovie, SiteWavveMovie

class MovieSearch(object):
    @staticmethod
    def search_movie(movie_name, movie_year):
        try:
            movie_year = '%s' % movie_year
            movie_list = []

            #8년 전쟁 이란 vs 이라크
            split_index = -1
            is_include_kor = False
            for index, c in enumerate(movie_name):
                if app.config['config']['is_py2']:
                    if ord(u'가') <= ord(c) <= ord(u'힣'):
                        is_include_kor = True
                        split_index = -1
                    elif ord('a') <= ord(c.lower()) <= ord('z'):
                        is_include_eng = True
                        if split_index == -1:
                            split_index = index
                    elif ord('0') <= ord(c.lower()) <= ord('9') or ord(' '):
                        pass
                    else:
                        split_index = -1
                else:
                    if (u'가') <= (c) <= (u'힣'):
                        is_include_kor = True
                        split_index = -1
                    elif ('a') <= (c.lower()) <= ('z'):
                        is_include_eng = True
                        if split_index == -1:
                            split_index = index
                    elif ('0') <= (c.lower()) <= ('9') or (' '):
                        pass
                    else:
                        split_index = -1

            if is_include_kor and split_index != -1:
                kor = movie_name[:split_index].strip()
                eng = movie_name[split_index:].strip()
            else:
                kor = None
                eng = None
            logger.debug('SEARCH_MOVIE : [%s] [%s] [%s] [%s]' % (movie_name, is_include_kor, kor, eng))

            movie_list = MovieSearch.search_movie_web(movie_list, movie_name, movie_year)
            if movie_list and movie_list[0]['score'] == 100:
                logger.debug('SEARCH_MOVIE STEP 1 : %s' % movie_list)
                return is_include_kor, movie_list

            if kor is not None:
                movie_list = MovieSearch.search_movie_web(movie_list, kor, movie_year)
                if movie_list and movie_list[0]['score'] == 100:
                    logger.debug('SEARCH_MOVIE STEP 2 : %s' % movie_list)
                    return is_include_kor, movie_list

            if eng is not None:
                movie_list = MovieSearch.search_movie_web(movie_list, eng, movie_year)
                if movie_list and movie_list[0]['score'] == 100:
                    logger.debug('SEARCH_MOVIE STEP 3 : %s' % movie_list)
                    return is_include_kor, movie_list

            #검찰측의 죄인 検察側の罪人. Kensatsu gawa no zainin. 2018.1080p.KOR.FHDRip.H264.AAC-RTM
            # 영어로 끝나지전은 한글
            # 그 한글중 한글로 시작하지 않는곳까지
            if kor is not None:
                tmps = kor.split(' ')
                index = -1
                for i in range(len(tmps)):
                    if app.config['config']['is_py2']:
                        if ord(u'가') <= ord(tmps[i][0]) <= ord(u'힣') or ord('0') <= ord(tmps[i][0]) <= ord('9'):
                            pass
                        else:
                            index = i
                            break
                    else:
                        if (u'가') <= (tmps[i][0]) <= (u'힣') or ('0') <= (tmps[i][0]) <= ('9'):
                            pass
                        else:
                            index = i
                            break
                if index != -1:
                    movie_list = MovieSearch.search_movie_web(movie_list, ' '.join(tmps[:index]), movie_year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP 4 : %s' % movie_list)
                        return is_include_kor, movie_list

            #if is_plex == False:
            if True:
                # 95점이면 맞다고 하자. 한글로 보내야하기때문에 검색된 이름을..
                if movie_list and movie_list[0]['score'] == 95:
                    movie_list = MovieSearch.search_movie_web(movie_list, movie_list[0]['title'], movie_year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP 5 : %s' % movie_list)
                        return is_include_kor, movie_list

            # IMDB
            if is_include_kor == False:
                movie = MovieSearch.search_imdb(movie_name.lower(), movie_year)
                if movie is not None:
                    movie_list = MovieSearch.search_movie_web(movie_list, movie['title'], movie_year)
                    if movie_list and movie_list[0]['score'] == 100:
                        logger.debug('SEARCH_MOVIE STEP IMDB : %s' % movie_list)
                        return is_include_kor, movie_list

            logger.debug('SEARCH_MOVIE STEP LAST : %s' % movie_list)
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        return is_include_kor, movie_list

    @staticmethod
    def movie_append(movie_list, data):
        try:
            exist_data = None
            for tmp in movie_list:
                if tmp['id'] == data['id']:
                    #flag_exist = True
                    exist_data = tmp
                    break
            #if exist_data is not None:
                #movie_list.remove(exist_data)
            movie_list.append(data)
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

        return

    @staticmethod
    def get_movie_info_from_home(url):
        try:
            from framework.common.daum import headers, session
            from system.logic_site import SystemLogicSite
            res = session.get(url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
            data = res.text

            #html = lxml.html.document_fromstring(requests.get(url).text)
            html = lxml.html.document_fromstring(data)
            movie = None
            try:
                movie = html.get_element_by_id('movieEColl')
            except Exception as exception:
                pass
            if movie is None:
                return None

            title_tag = movie.get_element_by_id('movieTitle')
            a_tag = title_tag.find('a')
            href = a_tag.attrib['href']
            title = a_tag.find('b').text_content()

            # 2019-08-09
            tmp = title_tag.text_content()
            #tmp_year = movie_year
            tmp_year = ''
            match = re.compile(r'(?P<year>\d{4})\s%s' % u'제작').search(tmp)

            more = {}
            if match:
                tmp_year = match.group('year')
                more['eng_title'] = tmp.replace(title, '').replace(tmp_year, '').replace(u'제작', '').replace(u',', '').strip()

            country_tag = movie.xpath('//div[3]/div/div[1]/div[2]/dl[1]/dd[2]')
            country = ''
            if country_tag:
                country = country_tag[0].text_content().split('|')[0].strip()
                logger.debug(country)
            more['poster'] = movie.xpath('//*[@id="nmovie_img_0"]/a/img')[0].attrib['src']
            more['title'] = movie.xpath('//*[@id="movieTitle"]/span')[0].text_content()
            tmp = movie.xpath('//*[@id="movieEColl"]/div[3]/div/div[1]/div[2]/dl')
            more['info'] = []
            #for t in tmp:
            #    more['info'].append(t.text_content().strip())
            #more['info'].append(tmp[0].text_content().strip())
            more['info'].append(country_tag[0].text_content().strip())

            #2019-09-07
            logger.debug(more['info'][0])
            tmp = more['info'][0].split('|')
            if len(tmp) == 5:
                more['country'] = tmp[0].replace(u'외', '').strip()
                more['genre'] = tmp[1].replace(u'외', '').strip()
                more['date'] = tmp[2].replace(u'개봉', '').strip()
                more['rate'] = tmp[3].strip()
                more['during'] = tmp[4].strip()
            elif len(tmp) == 4:
                more['country'] = tmp[0].replace(u'외', '').strip()
                more['genre'] = tmp[1].replace(u'외', '').strip()
                more['date'] = ''
                more['rate'] = tmp[2].strip()
                more['during'] = tmp[3].strip()
            elif len(tmp) == 3:
                more['country'] = tmp[0].replace(u'외', '').strip()
                more['genre'] = tmp[1].replace(u'외', '').strip()
                more['date'] = ''
                more['rate'] = ''
                more['during'] = tmp[2].strip()
            daum_id = href.split('=')[1]
            return {'movie':movie, 'title':title, 'daum_id':daum_id, 'year':tmp_year, 'country':country, 'more':more}

        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @staticmethod
    def search_movie_web(movie_list, movie_name, movie_year):
        try:
            #movie_list = []
            #url = 'https://suggest-bar.daum.net/suggest?id=movie&cate=movie&multiple=1&mod=json&code=utf_in_out&q=%s' % (py_urllib.quote(movie_name.encode('utf8')))
            url = f"https://movie.daum.net/api/search?q={py_urllib.quote(movie_name.encode('utf8'))}&t=movie&page=1&size=20"
            #from . import headers, cookies
            #res = Logic.session.get(url, headers=headers, cookies=cookies)
            # from framework.common.daum import headers, session
            # from system.logic_site import SystemLogicSite
            # res = session.get(url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
            # data = res.json()
            data = requests.get(url).json()
            for idx, item in enumerate(data['result']['search_result']['documents']):
                item = item['document']
                if idx > 50:
                    break
                title = item['titleKoreanHanl']
                movieId = item['movieId']
                year = item['productionYear']
                title_en = item['titleEnglishHanl']

            score = 85
            movie_cmp = re.sub('[\\/:*?"<>|]', '', movie_name)
            title = re.sub('[\\/:*?"<>|]', '', title)
            logger.debug('smw - first title:%s', title)
            if title == movie_cmp and int(year) == int(movie_year):
                score = 95
            ##elif tmps[0].find(movie_cmp) != -1 and int(tmps[3]) == int(movie_year):
                ##score = 95
            elif int(year) == int(movie_year) or abs(int(year) - int(movie_year)) <= 1:
                score = score + 6
            else:
                score -= idx * 5

            if score < 10:
                score = 10
            MovieSearch.movie_append(movie_list, {'id':movieId, 'title':title, 'year':year, 'score':score})
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

        try:
            url = 'https://search.daum.net/search?nil_suggest=btn&w=tot&DA=SBC&q=%s%s' % ('%EC%98%81%ED%99%94+', py_urllib.quote(movie_name.encode('utf8')))
            ret = MovieSearch.get_movie_info_from_home(url)
            if ret is not None:

                # 부제목때문에 제목은 체크 하지 않는다.
                # 홈에 검색한게 년도도 같다면 score : 100을 주고 다른것은 검색하지 않는다.
                if ret['year'] == movie_year:
                    score = 100
                    need_another_search = False
                else:
                    score >= 90
                    need_another_search = True
                MovieSearch.movie_append(movie_list, {'id':ret['daum_id'], 'title':ret['title'], 'year':ret['year'], 'score':score, 'country':ret['country'], 'more':ret['more']})

                logger.debug('need_another_search : %s' % need_another_search)

                movie = ret['movie']
                if need_another_search:
                    tmp = movie.find('div[@class="coll_etc"]')
                    if tmp is not None:
                        tag_list = tmp.findall('.//a')
                        first_url = None
                        for tag in tag_list:
                            match = re.compile(r'(.*?)\((.*?)\)').search(tag.text_content())
                            if match:
                                daum_id = tag.attrib['href'].split('||')[1]
                                score = 80
                                if match.group(1) == movie_name and match.group(2) == movie_year:
                                    first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                                elif match.group(2) == movie_year and first_url is not None:
                                    first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                                MovieSearch.movie_append(movie_list, {'id':daum_id, 'title':match.group(1), 'year':match.group(2), 'score':score})
                                #results.Append(MetadataSearchResult(id=daum_id, name=match.group(1), year=match.group(2), score=score, lang=lang))
                        logger.debug('first_url : %s' % first_url)
                        if need_another_search and first_url is not None:
                            new_ret = MovieSearch.get_movie_info_from_home(first_url)
                            MovieSearch.movie_append(movie_list, {'id':new_ret['daum_id'], 'title':new_ret['title'], 'year':new_ret['year'], 'score':100, 'country':new_ret['country'], 'more':new_ret['more']})
                #시리즈
                    tmp = movie.find('.//ul[@class="list_thumb list_few"]')
                    logger.debug('SERIES:%s' % tmp)
                    if tmp is not None:
                        tag_list = tmp.findall('.//div[@class="wrap_cont"]')
                        first_url = None
                        score = 80
                        for tag in tag_list:
                            a_tag = tag.find('a')
                            daum_id = a_tag.attrib['href'].split('||')[1]
                            daum_name = a_tag.text_content()
                            span_tag = tag.find('span')
                            year = span_tag.text_content()
                            logger.debug('daum_id:%s %s %s' % (daum_id, year, daum_name))
                            if daum_name == movie_name and year == movie_year:
                                first_url = 'https://search.daum.net/search?%s' % a_tag.attrib['href']
                            elif year == movie_year and first_url is not None:
                                first_url = 'https://search.daum.net/search?%s' % tag.attrib['href']
                            MovieSearch.movie_append(movie_list, {'id':daum_id, 'title':daum_name, 'year':year, 'score':score})
                            logger.debug('first_url : %s' % first_url)
                        if need_another_search and first_url is not None:
                            new_ret = MovieSearch.get_movie_info_from_home(first_url)
                            MovieSearch.movie_append(movie_list, {'id':new_ret['daum_id'], 'title':new_ret['title'], 'year':new_ret['year'], 'score':100, 'country':new_ret['country'], 'more':new_ret['more']})
            try:
                movie_list = list(reversed(sorted(movie_list, key=lambda k: k['score'])))
                logger.debug('smw - id: %s, score:%s, myear:%s, year:%s', movie_list[0]['id'], movie_list[0]['score'], movie_year, movie_list[0]['year'])
                #id_url = 'http://movie.daum.net/data/movie/movie_info/detail.json?movieId=%s' % movie_list[0]['id']
                id_url = "https://movie.daum.net/api/movie/%s/main" % movie_list[0]['id']
                #from . import headers, cookies
                #root = session.get_tree(id_url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
                # from framework.common.daum import headers, session
                # from system.logic_site import SystemLogicSite
                # res = session.get(id_url, headers=headers, cookies=SystemLogicSite.get_daum_cookies())
                #meta_data = res.json()
                logger.debug('smw - more search')
                meta_data = requests.get(id_url).json()
                if meta_data is not None:
                    logger.debug('smw - more search....ing')
                    logger.debug('smw - title:%s', meta_data['movieCommon']['titleKorean'])
                    logger.debug('smw - originaltitle:%s', meta_data['movieCommon']['titleEnglish'])
                    logger.debug('smw - year:%s', meta_data['movieCommon']['productionYear'])
                    logger.debug('smw - country:%s', meta_data['movieCommon']['productionCountries'])
                    logger.debug('smw - genre:%s', meta_data['movieCommon']['genres'])
                    if len(meta_data['movieCommon']['countryMovieInformation']) > 0:
                        for country in meta_data['movieCommon']['countryMovieInformation']:
                            if country['country']['id'] == 'KR':
                                mpaa = country['admissionCode']
                                runtime = country['duration']
                                logger.debug('smw - admissionCode:%s', country['admissionCode'])
                                logger.debug('smw - duration:%s', country['duration'])

                    #logger.debug('smw - meta_data %s', meta_data)
                    if int(movie_list[0]['year']) == 0:
                        movie_list[0]['year'] = py_unicode(meta_data['movieCommon']['productionYear'])
                    elif int(movie_year) == int(meta_data['movieCommon']['productionYear']):
                        movie_list[0]['year'] = py_unicode(meta_data['movieCommon']['productionYear'])
                        movie_list[0]['score'] = movie_list[0]['score'] + 5

                    movie_list[0]['title'] = meta_data['movieCommon']['titleKorean']
                    logger.debug('smw - eng title:%s', meta_data['movieCommon']['titleEnglish'])

                    movie_list[0].update({'more':{'eng_title':"", 'rate':"", 'during':"", 'genre':[]}})
                    
                    if mpaa:
                        movie_list[0]['more']['rate'] = mpaa
                        logger.debug('smw - rate:%s', movie_list[0]['more']['rate'])
                    if runtime:
                        movie_list[0]['more']['during'] = py_unicode(runtime)
                    
                    movie_list[0]['more']['eng_title'] = py_unicode(meta_data['movieCommon']['titleEnglish'])
                    logger.debug('smw - eng_title:%s', movie_list[0]['more']['eng_title'])
                    movie_list[0]['country'] = py_unicode(meta_data['movieCommon']['productionCountries'])
                    logger.debug('smw - country:%s', movie_list[0]['more']['country'])
                    movie_list[0]['more']['genre'].append(meta_data['movieCommon']['genres'])
                    logger.debug('smw - genre:%s', movie_list[0]['more']['genre'])
            except Exception as exception:
                pass
                #logger.error('Exception:%s', e)
                #logger.error(traceback.format_exc())
        except Exception as e:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
        movie_list = list(reversed(sorted(movie_list, key=lambda k:k['score'])))
        return movie_list

    @staticmethod
    def search_imdb(title, year):
        try:

            year = int(year)
            title = title.replace(' ', '_')
            url = 'https://v2.sg.media-imdb.com/suggestion/%s/%s.json' % (title[0], title)
            #logger.debug(url)
            tmp = requests.get(url).json()
            if 'd' in tmp:
                for t in tmp['d']:
                    title_imdb = t['l'].lower().replace("'", '').replace(':', '').replace('&', 'and').replace('?', '')
                    #logger.debug(title_imdb)
                    #logger.debug(title.lower().replace("'", '').replace('.', ' ').replace('_', ' '))
                    if title.lower().replace("'", '').replace('.', ' ').replace('_', ' ') == title_imdb and 'y' in t and t['y'] == year:
                        return {'id':t['id'], 'title':t['l'], 'year':year, 'score':100}
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
