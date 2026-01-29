import sys
import logging
import _thread
import cerberus.database.client as dbcli
from urllib.parse import urlparse, parse_qsl
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from pathlib import Path

# Start a simple http server to publish the cerberus status file content
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    requests_served = 0

    def do_GET(self):
        if self.path == "/":
            self.do_status()
        elif self.path.startswith("/history"):
            self.do_history()
        elif self.path == "/analyze":
            self.do_analyze()
        elif self.path.startswith("/analysis"):
            self.do_analysis()

    def do_status(self):
        self.send_response(200)
        self.end_headers()
        status_path = "/tmp/cerberus_status"
        # Ensure the file exists before opening
        if not os.path.exists(status_path):
            logging.error('Cerberus status not set yet')
            return

        # Use 'with' to ensure the file is closed automatically
        with open(status_path, "rb") as f:
            self.wfile.write(f.read())
        SimpleHTTPRequestHandler.requests_served = SimpleHTTPRequestHandler.requests_served + 1

    def do_history(self):
        parsed = urlparse(self.path)
        try:
            loopback = int(float(dict(parse_qsl(parsed.query))["loopback"]) * 60)
        except Exception:
            loopback = 3600
        try:
            dbcli.query(loopback)
            self.send_response(200)
            self.end_headers()
            with open("./history/cerberus_history.json", "rb") as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(404, "Encountered the following error: %s. Please retry" % e)

    def do_analyze(self):
        try:
            self.send_response(200)
            self.end_headers()
            with open("./history/analysis.html", "rb") as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(404, "Encountered the following error: %s. Please retry" % e)

    def do_analysis(self):
        formdata = dict(parse_qsl(urlparse(self.path).query, keep_blank_values=True))
        for key in ["issue", "name", "component"]:
            formdata[key] = formdata[key].strip().split(",")
            if not formdata[key]:
                formdata[key] = ()
            else:
                formdata[key] = tuple(value.strip() for value in formdata[key] if value.strip())
        try:
            dbcli.custom_query(formdata)
            self.send_response(200)
            self.end_headers()
            with open("./history/cerberus_analysis.json", "rb") as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(404, "Encountered the following error: %s. Please retry" % e)

def create_folder(folder_name):
    try: 
        folder_path = Path(folder_name)

        if not folder_path.is_dir():
            os.mkdir(folder_name)
    except Exception as e:
        logging.error('exception creating folder' + str(e))

def start_server(address):
    server = address[0]
    port = address[1]
    httpd = HTTPServer(address, SimpleHTTPRequestHandler)
    logging.info("Starting http server at http://%s:%s\n" % (server, port))
    try:
        _thread.start_new_thread(httpd.serve_forever, ())
        create_folder("./history")
        
    except Exception:
        logging.error(
            "Failed to start the http server \
                      at http://%s:%s"
            % (server, port)
        )
        sys.exit(1)
