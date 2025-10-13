#### Set base image (host OS)
FROM python:3.11-slim

#### By default, listen on port 8080
EXPOSE 8080/tcp

#### Set the working directory in the container
WORKDIR /

ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ> /etc/timezone

#### Copy the dependencies file to the working directory

COPY requirements.txt .
COPY wheelhouse/ ./wheelhouse/
#### Install any dependencies
RUN pip install --no-index --find-links=wheelhouse -r requirements.txt

#### Copy the content of the local src directory to the working directory
COPY . .

#### Specify the command to run on container start using Waitress
CMD ["gunicorn","-w","32","-k","gevent","--worker-connections","1000","-b","0.0.0.0:8080","run:application"]
