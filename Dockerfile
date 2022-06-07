FROM argoproj/argocli:v3.3.6 AS argo-builder
FROM alpine:3.16
WORKDIR /app

LABEL version="1.0.0"
LABEL repository="https://github.com/inarix/potential-fortnigh"
LABEL homepage="https://github.com/inarix/potential-fortnigh"
LABEL maintainer="Alexandre Saison <alexandre.saison@inarix.com>"

# install required for entrypoint.sh and AWS AUTH AUTHENTICATOR
RUN apk add --no-cache ca-certificates curl jq bash groff less binutils mailcap make && curl -o aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/1.19.6/2021-01-05/bin/linux/amd64/aws-iam-authenticator &&\
    chmod +x ./aws-iam-authenticator &&\
    mkdir -p $HOME/bin && cp ./aws-iam-authenticator $HOME/bin/aws-iam-authenticator && export PATH=$PATH:$HOME/bin &&\
    echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc &&\
    source ~/.bashrc

# Install python/pip
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 py3-pip && ln -sf python3 /usr/bin/python && python -m ensurepip && pip install --no-cache --upgrade pip setuptools

# Install Glib 'cause does aws install does not work on ALPINE
RUN python -m pip install --upgrade awscli s3cmd python-magic

COPY --from=argo-builder /bin/argo /usr/local/bin/argo
COPY Makefile /app
COPY . /app

RUN python -m pip install -r requirements.txt


ENTRYPOINT ["/app/entrypoint.sh"]
