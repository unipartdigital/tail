FROM fedora

RUN dnf install -y arm-none-eabi-gcc arm-none-eabi-newlib make srecord \
		   git-core ; \
    dnf clean all

ADD . /opt/tail

RUN git -C /opt/tail submodule update --init

CMD make -C /opt/tail/firmware
