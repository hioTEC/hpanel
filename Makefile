PREFIX  ?= /usr/local
BINDIR  ?= $(PREFIX)/bin
DATADIR ?= $(PREFIX)/share/dotpanel

INSTALL         ?= install
INSTALL_PROGRAM ?= $(INSTALL) -m 755
INSTALL_DATA    ?= $(INSTALL) -m 644

.PHONY: all install uninstall check shellcheck

all: check

install:
	mkdir -p "$(DESTDIR)$(BINDIR)" "$(DESTDIR)$(DATADIR)/templates/secrets"
	$(INSTALL_PROGRAM) bin/dot  "$(DESTDIR)$(BINDIR)/dot"
	$(INSTALL_PROGRAM) bin/dkey "$(DESTDIR)$(BINDIR)/dkey"
	$(INSTALL_DATA) templates/AGENTS.md             "$(DESTDIR)$(DATADIR)/templates/AGENTS.md"
	$(INSTALL_DATA) templates/secrets/dkey.conf     "$(DESTDIR)$(DATADIR)/templates/secrets/dkey.conf"
	$(INSTALL_DATA) templates/secrets/keys.env.template "$(DESTDIR)$(DATADIR)/templates/secrets/keys.env.template"
	$(INSTALL_DATA) templates/secrets/dkey.providers.example.json "$(DESTDIR)$(DATADIR)/templates/secrets/dkey.providers.example.json"

uninstall:
	rm -f "$(DESTDIR)$(BINDIR)/dot"
	rm -f "$(DESTDIR)$(BINDIR)/dkey"
	rm -rf "$(DESTDIR)$(DATADIR)"

check:
	sh -n bin/dot
	sh -n bin/dkey
	bash -n bin/dot
	bash -n bin/dkey

shellcheck:
	shellcheck bin/dot  bin/dkey  tests/run.sh || true
