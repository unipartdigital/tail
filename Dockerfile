FROM unipartdigital/firmware-tester

WORKDIR /opt/tail

ADD . .

RUN git submodule update --init

CMD make -C firmware
