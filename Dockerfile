FROM python:3.8

RUN useradd -ms /bin/bash basil
RUN mkdir -p /opt/basil /etc/basil /var/log/basil /opt/basil/static && \
    chown -R basil:basil /opt/basil && \
    chown -R basil:basil /etc/basil && \
    chown -R basil:basil /var/log/basil && \
    chown -R basil:basil /opt/basil/static

WORKDIR /opt/basil

RUN pip3 install pipenv

USER basil

COPY ./Pipfile* /opt/basil/
RUN pipenv sync

COPY ./run.py ./entrypoint.sh /opt/basil/
COPY ./basil /opt/basil/basil

USER root
RUN chown -R basil:basil /opt/basil/* && chmod u+x /opt/basil/entrypoint.sh

USER basil

ENV BASIL_CONFIG=/etc/basil/config.json

# Volume for static files:
VOLUME /opt/basil/static

# Volume for config files:
VOLUME /etc/basil

# 8080 = HTTP API
EXPOSE 8080/tcp

ENTRYPOINT [ "/opt/basil/entrypoint.sh" ]
