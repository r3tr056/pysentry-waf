FROM alpine

# Step 2 : Settings up the environment
RUN apk add --no-cache python3-dev && pip3 install --upgrade pip

WORKDIR /app
COPY /requirements.txt /app

RUN pip3 install -r requirements.txt

COPY ["/waf", '/app']

EXPOSE 5007

ENTRYPOINT ["python3"]

CMD ["app.py"]