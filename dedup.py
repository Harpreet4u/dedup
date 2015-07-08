import hashlib
import json
import os
import time
import tornado
import tornado.web
from tornado.options import define, options
from bson.objectid import ObjectId
import backend

define("port", default=8888, help="port number", type=int)
define("debug", default=0, help="For debugging in dev", type=int)


class TornadoApplication(tornado.web.Application):

    UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

    def __init__(self):
        handlers = [
            (r"/?", RootHandler),
            (r"/upload/?", UploadHandler),
            (r"/download/?", DownloadHandler),
            (r"/delete/?", DeleteHandler),
        ]

        settings = dict(
            autoescape=None,
            debug=options.debug,
            gzip=True,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class RootHandler(tornado.web.RequestHandler):
    
    def get(self):
        """
            REST call for index.html for testing purpose.
            e.g. http://localhost:8888/
        """
        self.render("index.html")


class UploadHandler(tornado.web.RequestHandler):

    def post(self):
        """
            REST call for uploading file.
            Request type: multipart post request
            Returns: Json object with status and response_id params 
            e.g. http://localhost:8888/upload
        """
        file_data = self.request.files["file"][0]
        response_id = None
        if not file_data:
            status_msg = "failure"

        if options.debug:
            print file_data
        try:
            path = os.path.join(TornadoApplication.UPLOAD_DIR, file_data["filename"]) 
            file_handler = open(path, "w")
            file_handler.write(file_data["body"])

            # Database Entry:
            # Redis Hash: file_key(file:uniqueId) -> timestamp(ts), filehash(fh), filePath (fp)
            # Redis Hash file_hash_key(fh:hash_val): filehash -> fp and count(number of uniqueIds)
       
            response_id = str(ObjectId()) 
            file_key = "file:" + response_id
            
            pipe = backend.redis_file.pipeline()
            file_hash = hashlib.sha1(file_data["body"]).hexdigest()
            file_hash_key = "fh:" + file_hash

            old_file_path = backend.redis_file.hget(file_hash_key, "fp")
            if old_file_path:
                pipe.hset(file_key, "fp", old_file_path)
                pipe.hincrby(file_hash_key, "cnt", 1)
            else:
                pipe.hset(file_hash_key, "fp", path)
                pipe.hset(file_hash_key, "cnt", 1)
                pipe.hset(file_key, "fp", path)
            
            pipe.hset(file_key, "ts", int(time.time()))      
            pipe.hset(file_key, "fh", file_hash)
            pipe.execute()
            status_msg = "success"  
        except:
            status_msg = "failure"
        
        self.finish(json.dumps({"status": status_msg, "response_id": response_id}))


class DownloadHandler(tornado.web.RequestHandler):

    def get(self):
        """
            REST call for downloading file.
            params: id
            e.g. http://localhost:8888/download?id=abc123
        """
        file_id = self.get_argument("id", None)
        msg = ""
        if file_id:
            # For forcing browser to download it as a file.
            self.set_header("Content-Disposition", "attachment; filename=\""+file_id + "\"")
            self.set_header("Content-type", "application/octet-stream")
            buffer_size = 8192 # 8kb
            key = "file:" + str(file_id)
            file_path = backend.redis_file.hget(key, "fp")
            if file_path:
                with open(file_path) as file_handler:
                    while True:
                        data = file_handler.read(buffer_size)
                        if not data:
                            break
                        self.write(data)    
            else:
                msg = "File does not exists."
        else:
            msg = "Enter file id for downloading file."
        self.finish(json.dumps({"status": msg}))       


class DeleteHandler(tornado.web.RequestHandler):

    def get(self):
        """
            REST call for deleting file entry from Db.
            params: id
            e.g. http://localhost:8888/delete?id=abc123
        """
        file_id = self.get_argument("id", None)
        file_key = "file:"+file_id
        try:
            file_hash = backend.redis_file.hget(file_key, "fh")
            pipe = backend.redis_file.pipeline()
            file_hash_key = "fh:"+file_hash
            pipe.delete(file_key)
            if int(backend.redis_file.hget(file_hash_key, "cnt")) == 1:
                # Delete file from server as its last reference to file.
                os.remove(backend.redis_file.hget(file_hash_key, "fp"))
                pipe.delete(file_hash_key)
            else:
                # Decrements deleted reference to file.
                pipe.hincrby(file_hash_key, "cnt", -1)
            pipe.execute() 
            msg = "success" 
        except:
            msg = "failure"
        self.finish(json.dumps({"status": msg}))
        
def main():
    backend.init()
    print "Server Running..."
    tornado.options.parse_command_line()
    TornadoApplication().listen(options.port, xheaders=True)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
