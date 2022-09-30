run: bootstrap
	.twisted/bin/twistd -ny hagent.tac

bootstrap: .twisted

.twisted:
	virtualenv $@
	$@/bin/pip install twisted[tls]

.PHONY: run bootstrap
