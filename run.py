# run.py

from werkzeug.serving import run_simple # werkzeug development server
from app import create_app
from waitress import serve
application = create_app()
if __name__ == '__main__':
    # serve(application, host="0.0.0.0", port=8080)
    
    #run_simple('0.0.0.0', 5000, application, use_reloader=True, use_debugger=True, use_evalex=True)
    run_simple('127.0.0.1', 8080, application, use_reloader=True, use_debugger=True, use_evalex=True)
    
#docker run -d -p 6379:6379 redis
#docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' redisact