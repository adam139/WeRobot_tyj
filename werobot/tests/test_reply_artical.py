# -*- coding:utf-8 -*-

import hashlib
import time
import six

from nose.tools import raises
from werobot import WeRoBot
from werobot.utils import generate_token, to_text

from werobot.reply import create_reply,ArticlesReply,WeChatReply,Article
def test_signature_checker():
    token = generate_token()

    robot = WeRoBot(token)

    timestamp = str(int(time.time()))
    nonce = '12345678'

    sign = [token, timestamp, nonce]
    sign.sort()
    sign = ''.join(sign)
    if six.PY3:
        sign = sign.encode()
    sign = hashlib.sha1(sign).hexdigest()

    assert robot.check_signature(timestamp, nonce, sign)





def test_replay_artical():
    import re
    import werobot.testing
    robot = WeRoBot()


    def _make_xml(content):
        return """
            <xml>
            <ToUserName><![CDATA[toUser]]></ToUserName>
            <FromUserName><![CDATA[fromUser]]></FromUserName>
            <CreateTime>1348831860</CreateTime>
            <MsgType><![CDATA[text]]></MsgType>
            <Content><![CDATA[%s]]></Content>
            <MsgId>1234567890123456</MsgId>
            </xml>
        """ % content


        
    @robot.text
    def echo(message):
        import pdb
        pdb.set_trace()
        a1 = ArticlesReply(message=message,star=True,MsgType="news",ArticleCount=1)
        item = Article(title=u"Plone技术论坛",img="",description="最大的中文Plone技术社区",url="http://plone.315ok.org/")
        a1.add_article(item)

        return a1   

    tester = werobot.testing.WeTest(robot)

   
    replyobj = tester.send_xml(_make_xml("啊"))
    create_reply(replyobj)
     


