from distutils.core import setup

old_plugins = {'action': ['ShowProcessGraph.py', 'MetaCSV.py', 'metaCVS.py',
                          'ShowGraphIE.py', 'MetaTableEdit.py',
                          'ShowLatexSource.py', 'metaRadarDiagram.py',
                          'metaeditform.py'],
               'macro': ['metaRadarDiagram.py']}

setup(name='graphingwiki', version='0.1',
      author='Juhani Eronen, Joachim Viide, Aki Helin',
      author_email='exec@iki.fi',
      description='Graph handling for the Graphingwiki MoinMoin extension',
      packages=['graphingwiki'],
      package_dir={'graphingwiki': 'graphingwiki'},
      package_data={'graphingwiki': ['plugin/*/*.py']},
      scripts=['scripts/gwiki-rehash', 'scripts/gwiki-showgraph',
               'scripts/gwiki-debuggraph', 'scripts/gwiki-install',
               'scripts/moin-showpage', 'scripts/gwiki-get-tgz',
               'scripts/mm2gwiki.py', 'scripts/moin-editpage',
               'scripts/gwiki-xml-attachfile',
               'scripts/gwiki-xml-meta'])
