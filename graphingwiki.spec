# sitelib for noarch packages, sitearch for others (remove the unneeded one)
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?python_sitearch: %define python_sitearch %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)")}

%define 	rev 433
%define		date 20080421

Name:           graphingwiki
Version:        0
Release:        0.1.%{date}svn%{rev}%{?dist}
Summary:        Semantical extensions for MoinMoin

Group:          Applications/Internet
License:        MIT
URL:            http://graphingwiki.python-hosting.com/
Source0:        %{name}-svn%{rev}.tar.bz2
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

BuildArch:      noarch
BuildRequires:  python-devel

%description 
Graphingwiki

%package gwiki
Summary:        Semantical extensions for MoinMoin
Group:          Applications/Internet
Requires:	moin > 1.5.8
Requires: 	moin < 1.6

%description gwiki
Graphingwiki, a MoinMoin extension to augment Wiki pages with
semantic data and to visualise this data.

%package opencollab
Summary:        OpenCollab SDK
Group:          Applications/Internet

%description opencollab
OpenCollab SDK

%prep
%setup -q -n graphingwiki

%build
# Remove CFLAGS=... for noarch packages (unneeded)
cd graphingwiki; %{__python} setup.py build; cd ..
cd opencollab; %{__python} setup.py build

%install
rm -rf $RPM_BUILD_ROOT
cd graphingwiki
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT
cd ..
cd opencollab
%{__python} setup.py install -O1 --skip-build --root $RPM_BUILD_ROOT

rm -f $RPM_BUILD_ROOT%{_bindir}/mm2gwiki*

%clean
rm -rf $RPM_BUILD_ROOT

#%files


# For noarch packages: sitelib
%files gwiki
%defattr(-,root,root,-)
%{_bindir}/gwiki-*
%{_bindir}/moin-*
%{python_sitelib}/graphingwiki/*

%files opencollab
%defattr(-,root,root,-)
%{_bindir}/opencollab-*
%{python_sitelib}/opencollab/*

%changelog