FROM argoproj/argocli:v3.3.6 AS argo-builder
FROM python:3-alpine
WORKDIR /app

# Install AWS AUTH AUTHENTICATOR
RUN curl -o aws-iam-authenticator https://amazon-eks.s3.us-west-2.amazonaws.com/1.19.6/2021-01-05/bin/linux/amd64/aws-iam-authenticator &&\
    chmod +x ./aws-iam-authenticator &&\
    mkdir -p $HOME/bin && cp ./aws-iam-authenticator $HOME/bin/aws-iam-authenticator && export PATH=$PATH:$HOME/bin &&\
    echo 'export PATH=$PATH:$HOME/bin' >> ~/.bashrc &&\
    source ~/.bashrc

RUN apk add curl
# Install Glib 'cause does aws install does not work on ALPINE
RUN pip install --upgrade awscli s3cmd python-magic && \
    apk -v --purge del py-pip

# Since using argo to trigger runs, doesn't need to pip install other than metaflow
RUN python -m pip install metaflow==2.6.3

COPY --from=argo-builder /bin/argo /usr/local/bin/argo
COPY Makefile /app
COPY bookish.py /app
COPY entrypoint.sh /app

ENTRYPOINT [ "entrypoint.sh" ]
