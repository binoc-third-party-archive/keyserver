%define name python-jpake-server
%define pythonname JPakeServer
%define version 0.1
%define unmangled_version 0.1
%define unmangled_version 0.1
%define release 1

Summary: J-Pake server
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{pythonname}-%{unmangled_version}.tar.gz
License: MPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{pythonname}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Tarek Ziade <tarek@mozilla.com>
Requires: httpd memcached mod_wsgi python26 pylibmc python26-setuptools python-webob python-meld3 python-paste python-pastedeploy python-pastescript python-repoze-profile

Url: https://hg.mozilla.org/services

%description
=============
J-PAKE Server
=============

Implementation of the J-PAKE server.

See: https://wiki.mozilla.org/Services/Sync/SyncKey/J-PAKE


%prep
%setup -n %{pythonname}-%{unmangled_version} -n %{pythonname}-%{unmangled_version}

%build
python2.6 setup.py build

%install
mkdir -p %{buildroot}%{_sysconfdir}/jpake
install -m 0644 etc/jpake/jpake.wsgi %{buildroot}%{_sysconfdir}/jpake/jpake.wsgi
install -m 0644 etc/jpake/production.ini %{buildroot}%{_sysconfdir}/jpake/production.ini
mkdir -p %{buildroot}%{_sysconfdir}/httpd
mkdir -p %{buildroot}%{_sysconfdir}/httpd/conf.d
install -m 0644 etc/jpake/jpake.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/jpake.conf
python2.6 setup.py install --single-version-externally-managed --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT


%files -f INSTALLED_FILES

%dir %{_sysconfdir}/jpake/

%config(noreplace) %{_sysconfdir}/jpake/*

%config(noreplace) %{_sysconfdir}/httpd/conf.d/jpake.conf

%defattr(-,root,root)
