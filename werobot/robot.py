# -*- coding: utf-8 -*-
#!/home/plone/workspace/WeRobot/bin/python
import six
import werobot
import os
import inspect
import hashlib
import logging

from bottle import Bottle, request, response, abort, template

from werobot.config import Config, ConfigAttribute
from werobot.parser import parse_user_msg
from werobot.reply import create_reply,ArticlesReply,WeChatReply,Article
from werobot.utils import to_binary, to_text

__all__ = ['BaseRoBot', 'WeRoBot']


_DEFAULT_CONFIG = dict(
    SERVER="tornado",
    HOST="127.0.0.1",
    PORT="8888",
    Teken="plne2018"
)


class BaseRoBot(object):
    message_types = ['subscribe', 'unsubscribe', 'click',  'view',  # event
                     'text', 'image', 'link', 'location', 'voice']

    token = ConfigAttribute("TOKEN")
    session_storage = ConfigAttribute("SESSION_STORAGE")

    def __init__(self, token=None, logger=None, enable_session=True,
                 session_storage=None):
        self.config = Config(_DEFAULT_CONFIG)
        self._handlers = dict((k, []) for k in self.message_types)
        self._handlers['all'] = []
        if logger is None:
            import werobot.logger
            logger = werobot.logger.logger
        self.logger = logger

        if enable_session and session_storage is None:
            from .session.filestorage import FileStorage
            session_storage = FileStorage(
                filename=os.path.abspath("werobot_session")
            )
        self.config.update(
            TOKEN=token,
            SESSION_STORAGE=session_storage,

        )

    def handler(self, f):
        """
        Decorator to add a handler function for every messages
        """
        self.add_handler(f, type='all')
        return f

    def text(self, f):
        """
        Decorator to add a handler function for ``text`` messages
        """
        self.add_handler(f, type='text')
        return f

    def image(self, f):
        """
        Decorator to add a handler function for ``image`` messages
        """
        self.add_handler(f, type='image')
        return f

    def location(self, f):
        """
        Decorator to add a handler function for ``location`` messages
        """
        self.add_handler(f, type='location')
        return f

    def link(self, f):
        """
        Decorator to add a handler function for ``link`` messages
        """
        self.add_handler(f, type='link')
        return f

    def voice(self, f):
        """
        Decorator to add a handler function for ``voice`` messages
        """
        self.add_handler(f, type='voice')
        return f

    def subscribe(self, f):
        """
        Decorator to add a handler function for ``subscribe event`` messages
        """
        self.add_handler(f, type='subscribe')
        return f

    def unsubscribe(self, f):
        """
        Decorator to add a handler function for ``unsubscribe event`` messages
        """
        self.add_handler(f, type='unsubscribe')
        return f

    def click(self, f):
        """
        Decorator to add a handler function for ``click`` messages
        """
        self.add_handler(f, type='click')
        return f

    def key_click(self, key):
        """
        Shortcut for ``click`` messages
        @key_click('KEYNAME') for special key on click event
        """
        def wraps(f):
            argc = len(inspect.getargspec(f).args)

            @self.click
            def onclick(message, session=None):
                if message.key == key:
                    return f(*[message, session][:argc])
            return f

        return wraps

    def filter(self, *args):
        """
        Shortcut for ``text`` messages
        ``@filter("xxx")``, ``@filter(re.compile("xxx"))``
        or ``@filter("xxx", "xxx2")`` to handle message with special content
        """

        content_is_list = False

        if len(args) > 1:
            content_is_list = True
        else:
            target_content = args[0]
            if isinstance(target_content, six.string_types):
                target_content = to_text(target_content)

                def _check_content(message):
                    return message.content == target_content
            elif hasattr(target_content, "match") and callable(target_content.match):
                # 正则表达式什么的

                def _check_content(message):
                    return target_content.match(message.content)
            else:
                raise TypeError("%s is not a valid target_content" % target_content)

        def wraps(f):
            if content_is_list:
                for x in args:
                    self.filter(x)(f)
                return f
            argc = len(inspect.getargspec(f).args)

            @self.text
            def _f(message, session=None):
                if _check_content(message):
                    return f(*[message, session][:argc])

            return f

        return wraps

    def view(self, f):
        """
        Decorator to add a handler function for ``view event`` messages
        """
        self.add_handler(f, type='view')
        return f

    def add_handler(self, func, type='all'):
        """
        Add a handler function for messages of given type.
        """
        if not callable(func):
            raise ValueError("{} is not callable".format(func))

        self._handlers[type].append((func, len(inspect.getargspec(func).args)))

    def get_handlers(self, type):
        return self._handlers[type] + self._handlers['all']

    def get_reply(self, message):
        """
        Return the raw xml reply for the given message.
        """
        session_storage = self.config["SESSION_STORAGE"]

        id = None
        session = None
        if session_storage and hasattr(message, "source"):
            id = to_binary(message.source)
            session = session_storage[id]

        handlers = self.get_handlers(message.type)

        try:
            for handler, args_count in handlers:
                args = [message, session][:args_count]
                reply = handler(*args)
                if session_storage and id:
                    session_storage[id] = session
                if reply:
                    return reply
        except:
            self.logger.warning("Catch an exception", exc_info=True)

    def check_signature(self, timestamp, nonce, signature):
        sign = [self.config["TOKEN"], timestamp, nonce]
        sign.sort()
        sign = to_binary(''.join(sign))
        sign = hashlib.sha1(sign).hexdigest()
        return sign == signature


class WeRoBot(BaseRoBot):

    ERROR_PAGE_TEMPLATE = """
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf8" />
            <title>Error: {{e.status}}</title>
            <style type="text/css">
              html {background-color: #eee; font-family: sans;}
              body {background-color: #fff; border: 1px solid #ddd;
                    padding: 15px; margin: 15px;}
              pre {background-color: #eee; border: 1px solid #ddd; padding: 5px;}
            </style>
        </head>
        <body>
            <h1>Error: {{e.status}}</h1>
            <p>微信机器人不可以通过 GET 方式直接进行访问。</p>
            <p>想要使用本机器人，请在微信后台中将 URL 设置为 <pre>{{request.url}}</pre> 并将 Token 值设置正确。</p>

            <p>如果你仍有疑问，请<a href="http://werobot.readthedocs.org/en/%s/">阅读文档</a>
        </body>
    </html>
    """ % werobot.__version__

    @property
    def wsgi(self):
        if not self._handlers:
            raise
        app = Bottle()
# 如果是get请求，此为微信的验证请求
        @app.get('<t:path>')
        def echo(t):
            if not self.check_signature(
                request.query.timestamp,
                request.query.nonce,
                request.query.signature
            ):
                return abort(403)
            return request.query.echostr

        @app.post('<t:path>')
        def handle(t):
            if not self.check_signature(
                request.query.timestamp,
                request.query.nonce,
                request.query.signature
            ):
                return abort(403)

#            import pdb
#            pdb.set_trace()
            body = request.body.read()
# 分析原始xml，返回名类型message实例            
            message = parse_user_msg(body)
            logging.info("Receive message %s" % message)
#根据信息类型查询已注册的handler,返回被handler装饰的函数，参数为对应类型message实例            
            reply = self.get_reply(message)
            if not reply:
                self.logger.warning("No handler responded message %s"
                                    % message)
                return ''
#设置返回文档头            
            response.content_type = 'application/xml'
#创建回复消息             
            return create_reply(reply, message=message)

        @app.error(403)
        def error403(error):
            return template(self.ERROR_PAGE_TEMPLATE,
                            e=error, request=request)

        return app

    def run(self, server=None, host=None,
            port=None, enable_pretty_logging=True):
        if enable_pretty_logging:
            from werobot.logger import enable_pretty_logging
            enable_pretty_logging(self.logger)
        if server is None:
            server = self.config["SERVER"]
        if host is None:
            host = self.config["HOST"]
        if port is None:
            port = self.config["PORT"]
        self.wsgi.run(server=server, host=host, port=port)
        
if __name__ =="__main__":
    import werobot
    robot = werobot.WeRoBot(token='plone2018')

    @robot.subscribe
    def echo(message):
        return u"欢迎关注我们！我们提供全面的plone技术咨询服务。"

    @robot.unsubscribe
    def echo(message):
        return u"感谢您一直以来对我们的关注和支持，我们会加倍努力，让您士别三日，刮目相看！"    

    @robot.text
    def echo(message):
#        import pdb
#        pdb.set_trace()
        a1 = ArticlesReply(message=message,star=True,MsgType="news",ArticleCount=1)
        item = Article(title=u"Plone技术论坛",img="",description="最大的中文Plone技术社区",url="http://plone.315ok.org/")
        a1.add_article(item)

        return a1 

    @robot.voice
    def echotext(message):
        return u"你需要何种帮助？"


    robot.run(server="tornado")        
