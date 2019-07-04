FROM fedora

RUN dnf install -y arm-none-eabi-gcc arm-none-eabi-newlib make srecord \
		   git-core ; \
    dnf clean all

ADD . /opt/tail

CMD make -C /opt/tail/firmware
