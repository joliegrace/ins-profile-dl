#pylint:disable=E0001
import requests
import time
import calendar
import json
import os
from os import  path
from tqdm import tqdm
import  re
import cgi


BASE_URL = 'https://www.instagram.com'
LOGIN_ENDPOINT = '/accounts/login/ajax/'
#QUERY_ENDPOINT = '/graphql/query/?query_id=17888483320059182'
QUERY_ENDPOINT = '/graphql/query/?query_hash=8c2a529969ee035a5063f2fc8602a0fd'
FOLLOW_ENDPOINT = "https://www.instagram.com/web/friendships/{}/follow/"
CONTENT_TYPE = 'application/x-www-form-urlencoded'
USER_AGENT = 'Mozilla/5.0 (Linux; Android 11; Redmi Note 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.52 Mobile Safari/537.36'
MEDIA_DL_DIR = 'InstagramDownload'
PROFILE_NAME_DIR = 'What?'
SSID_PATH = os.path.join("other","SessionId.txt")
TYPEIMAGE = 'GraphImage'
TYPEVIDEO = 'GraphVideo'
TYPESIDECAR = 'GraphSidecar'


def main():
	if os.path.exists(SSID_PATH):
		prepareScap()
	else:
 	   login()
	      
	
	
def login():
	print('----- Login to Instagram with username/email & password ----')
	username = input('>>Username or Email: ')
	password = input('>>Password: ')

	login_headers = {"user-agent":USER_AGENT}

	print(' >> Wait server authenticated login infomation.... <<')
	login_resp = requests.get(BASE_URL,
									headers=login_headers)

	cookies = []
	for item in login_resp.cookies:
		cookies.append(item.name + ':' + item.value)

	cookiesStr = '; '.join(map(str , cookies))
	csrftoken = login_resp.cookies.get('csrftoken')

	current_GMT = time.gmtime()
	timestamp = str(calendar.timegm(current_GMT))
	
	auth_headers = {"content-type":CONTENT_TYPE,
						     	 "user-agent":USER_AGENT,
						     	 "x-csrftoken":csrftoken,
						     	 "cookie":cookiesStr}
	form_payload = {'username':username,
							  'enc_password':'#PWD_INSTAGRAM_BROWSER:0:'+timestamp+':'+password}
							  			 
	auth_resp = requests.post(BASE_URL+LOGIN_ENDPOINT,headers=auth_headers,data=form_payload)

	AuthCheck(auth_resp)
	
	

def AuthCheck(response):
	resp = json.loads(response.content)
	if not resp['authenticated']:
		print('            Authenticate Failed !              ')
	else:
		print('            Authenticate Success            ')		
		sessionid = response.cookies.get('sessionid')
		if os.path.exists("other"):
			if os.path.exists(SSID_PATH):
				os.remove(SSID_PATH)
			os.rmdir("other")
		os.mkdir("other")
		f = open(SSID_PATH, "a")
		f.write(sessionid)
		f.close()	
		prepareScap()
		
		

def prepareScap():
	sessionid = open(SSID_PATH , "r").read()
	if(not sessionid):
		print('! Sessionid is empty, login again')
		login()
	else:
		Scap(sessionid)
	
	
def Scap(ssid):
	profile_name = input('>>Enter profile username : ') + '/'
	profile_headers = {'user-agent':USER_AGENT,
								  	'cookie':'sessionid=' + ssid}
	print('------------- Sending request.... -------------')
	profile_resp = requests.get(BASE_URL + '/' + profile_name, headers = profile_headers)
	csrftoken = profile_resp.cookies.get('csrftoken')
	if profile_resp.status_code == 200:
		resp = profile_resp.content
		if(not resp):
			print('------- ERROR ! -------')
		else:
			if un_login(resp):
				print('---- --Some Error like Session Timeout... ! try to login again?-- -----')
				login()
			else:
				profile_json = parse__json(True ,extract__profile__json(True , resp))
				USER_DICT = profile_json['user']
				global PROFILE_NAME_DIR 
				PROFILE_NAME_DIR = USER_DICT['full_name']
				print('>>>>>>> @'+USER_DICT['full_name'])
				print('>>>>>>> '+USER_DICT['biography'])
				print('>>>>>>> follower: '+str(USER_DICT['edge_followed_by']['count']))
				print('>>>>>>> all media: ' +str(USER_DICT['edge_owner_to_timeline_media']['count']))
				id = USER_DICT["id"]
				# I has finding and try using url for scap private profile but it didn't work for me ! I don't know why ^_^ '
				if len(USER_DICT['edge_owner_to_timeline_media']['edges'] ) <= 0:
				 	if USER_DICT['is_private']:
				 		print('---------- this profile is Private ! ------------')
				 		profile_headers.update({'x-csrftoken':csrftoken})
				 		follow_resp = requests.post(FOLLOW_ENDPOINT.format(str(id)), headers = profile_headers, allow_redirects = False).status_code
				 		if follow_resp == 302:
				 			print('√ Follow request has sending... go back here when this profile accept the follow request ! LOL =))) ')
				 		
				 	else:
				 		print('------- Cannot find any media in this Profile ^_^ -------')
				else:
					print('Counting all page of profile @'+USER_DICT['full_name']+'....')
					Real__Scrap(USER_DICT, id, ssid, profile_headers)
					
	elif profile_resp.status_code == 404:
		print('------------- 404 PAGE NOT FOUND ! -----------')
	else:
		print('------------------ ERROR ! ---------------')
		
def Real__Scrap(dict,id , ssid, header):
	count = 0
	NEXT_DICT = []
	while True:
		print('[Counting]> profile @'+dict['full_name']+' >Page: ' + str(count+1))
		
		if count <= 0:
			cursor = ""
		else:
			cursor = NEXT_DICT[count-1]['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
		next_query = {'variables':'{'+'"id":"{}","first":{},"after":"{}"'.format(id,'12',cursor)+'}'}
		next_resp = requests.get(BASE_URL+QUERY_ENDPOINT,params=next_query, headers = header).content
		next_json = parse__json(False, extract__profile__json(False,next_resp))
		NEXT_DICT.append(next_json)
		if not next_json['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']:
			break
		count +=1
	extract__dict(NEXT_DICT)
	
		
						
def extract__profile__json(isFirst , str):
	jsons = "{ }"
	if isFirst:
		regex = rb".*window._sharedData\s*=\s*(.+?});"
		match = re.search(regex, str)
		jsons = json.loads(match.group(1))
	else:
		jsons = json.loads(str)
	return jsons
	
def parse__json(isFirst , json):
	j = '{ }'
	try:
		if isFirst:
			j = json['entry_data']['ProfilePage'][0]['graphql']
		else:
			j = json["data"]
		return j
	except:
		print('--- ERROR ---')
	    
def un_login(resp):
	    regex = r'.*Login\s*•\s+Instagram'
	    isMatch = re.search(regex , resp.decode('utf-8'))
	    if isMatch:
	    	return True
	    else:
	    	return False
	    
def extract__dict(dict):
	    count = 0
	    for item in dict:
    		for edges in item['user']['edge_owner_to_timeline_media']['edges']:
	    		extract__(edges['node'], str(count + 1))
	    	count +=1
	    
def extract__image(node):
    return node['display_url']

def extract__video(node):
    return node['video_url']

def extract__(node, page):
    type = node['__typename']
    if type == TYPEIMAGE:
        download(extract__image(node), page)
    elif type == TYPEVIDEO:
        download(extract__video(node), page)
    elif type == TYPESIDECAR:
        node_child = node['edge_sidecar_to_children']['edges']
        for item in node_child:
            node_child_of_child = item['node']
            child_type = node_child_of_child['__typename']
            download(extract__image(node_child_of_child), page) if child_type == TYPEIMAGE else download(extract__video(node_child_of_child), page)
            

def download(url, page):
    buffer_size = 1024
    response = requests.get(url, stream=True)
    file_size = int(response.headers.get("Content-Length", 0))
    default_filename = get_filename(url)
    content_disposition = response.headers.get("Content-Disposition")
    if content_disposition:
        value, params = cgi.parse_header(content_disposition)
        filename = params.get("filename", default_filename)
    else:
        filename = default_filename
    progress = tqdm(response.iter_content(buffer_size), f"Page: {page} > Saved {filename}...", total=file_size, unit="B", unit_scale=True, unit_divisor=1024)
    media_path = MEDIA_DL_DIR + '/' + PROFILE_NAME_DIR 
    full_path = media_path + '/' + "Page " + str(page)
    if not os.path.exists(MEDIA_DL_DIR):
    	 os.mkdir(MEDIA_DL_DIR)
    if not os.path.exists(media_path):
    	os.mkdir(media_path)
    if not os.path.exists(full_path):
    	os.mkdir(full_path)
    with open(full_path + '/' + filename, "wb") as f:
        for data in progress.iterable:
            f.write(data)
            progress.update(len(data))


def get_filename(url):
     fragment_removed = url.split("#")[0]  
     query_string_removed = fragment_removed.split("?")[0]
     scheme_removed = query_string_removed.split("://")[-1].split(":")[-1]
     if scheme_removed.find("/") == -1:
       return ""
     return path.basename(scheme_removed)
     
       	    
if __name__ == '__main__':
    main()
