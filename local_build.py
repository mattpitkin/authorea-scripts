#!/usr/bin/env python
from __future__ import division, print_function

"""
This script generates a file to use for building authorea papers, and then runs
latex on them.

Requires python >= 2.6 (3.x should work, too)

The key assumptions are:
* ``layout.md`` exists in the article (I think it always does in Authorea)
* ``preamble.tex`` and/or``header.tex``, ``title.tex``, and
  ``bibliobgraphy/biblio.bib`` exist (I think these are created normally in a
    new Authorea article)
* ``posttitle.tex`` exists.  This one you'll have to create, containing
  everything you want after the title but before the beginning of the document.
  If it doesn't exist that's ok too, it'll just be ignored.
* Figures are in the ``figures`` directory (where authorea puts them), and in
  the correct place in the ``layout.md`` file.  A file named 'latexfigopts.json'
  can specify a dictionary for additional figure options (see the
  `FIGURE_DEFAULTS` below for what options that can be replaced).

"""

import os
import subprocess


#lots of dobule-{}'s are here because we use it as a formatting template below
MAIN_TEMPLATE = r"""
{preamblein}

{headerin}


\begin{{document}}

{titlecontent}

{sectioninputs}

\bibliography{{{bibloc}}}{{}}

\end{{document}}
"""

FIGURE_TEMPLATE = r"""
\begin{<figure_env>}[<placement>]
\begin{center}
\includegraphics[width=<width>]{<figfn>}
<caption>
\end{center}
\end{<figure_env>}
""".replace('{', '{{').replace('}', '}}').replace('<', '{').replace('>', '}')

FIGURE_DEFAULTS = {'placement': '', 'width': '1\columnwidth', 'figure_env': 'figure'}


def get_input_string(filename, localdir, quotepath=True):
    if filename.endswith('.tex'):
        filename = filename[:-4]
    if quotepath:
        quote_chr = '"'
    else:
        quote_chr = ''
    return r'\input{' + quote_chr + os.path.join(os.path.abspath(localdir), filename) + quote_chr + '}'


def get_figure_string(filename, localdir):
    import json

    figdir, figfn = os.path.split(filename)
    figdir = os.path.join(localdir, figdir)

    figfnbase = os.path.splitext(figfn)[0]
    figfn = os.path.join(figdir, figfn)
    pdffn = os.path.join(figdir, figfnbase + '.pdf')
    epsfn = os.path.join(figdir, figfnbase + '.eps')

    if not os.path.exists(pdffn):
        pdffn = None
    if not os.path.exists(epsfn):
        epsfn = None

    if pdffn or epsfn:
        figfn = os.path.join(figdir, figfnbase)

    figfn = os.path.abspath(figfn)

    capfn = os.path.join(figdir, 'caption.tex')
    if os.path.exists(capfn):
        caption = r'\caption{ \protect\input{' + os.path.abspath(capfn) + '}}'
    else:
        caption = ''

    optsfn = os.path.join(figdir, 'latexfigopts.json')
    figopts = FIGURE_DEFAULTS.copy()
    if os.path.exists(optsfn):
        with open(optsfn) as f:
            optsjson = json.load(f)
        if not isinstance(optsjson, dict):
            raise ValueError('File "{0}" does not have a top-level dict'.format(optsfn))
        for k in FIGURE_DEFAULTS.keys():
            v = optsjson.pop(k, None)
            if v is not None:
                figopts[k] = v
        if len(optsjson) != 0:
            raise ValueError('Entries in "{0}" that were not understood: {1}'.format(optsfn, optsjson))

    figopts.update(locals())
    return FIGURE_TEMPLATE.format(**figopts)


def build_authorea_latex(localdir, builddir, latex_exec, bibtex_exec, outname,
                         usetitle, dobibtex, npostbibcalls, openwith, titleinput,
                         dobuild):
    if not os.path.exists(builddir):
        os.mkdir(builddir)

    if not os.path.isdir(builddir):
        raise IOError('Requested build directory {0} is a file, not a '
                      'directory'.format(builddir))

    # generate the main tex file as a string
    if os.path.exists('preamble.tex'):
        preamblein = get_input_string('preamble', localdir)
    else:
        preamblein = ''
    if os.path.exists('header.tex'):
        headerin = get_input_string('header', localdir)
    else:
        headerin = ''

    if not headerin and not preamblein:
        print("Neither preable nor header found!  Proceeding, but that's rather weird")

    bibloc = os.path.join(os.path.abspath(localdir), 'bibliography', 'biblio')

    titlecontent = []
    if usetitle:
        if titleinput:
            titlestr = get_input_string('title', localdir)
        else:
            with open(os.path.join(os.path.abspath(localdir), 'title.tex')) as f:
                titlestr = f.read()
        titlecontent.append(r'\title{' + titlestr + '}')
    if os.path.exists(os.path.join(os.path.abspath(localdir), 'posttitle.tex')):
        titlecontent.append(get_input_string('posttitle', localdir))
    titlecontent = '\n'.join(titlecontent)

    sectioninputs = []
    with open(os.path.join(localdir, 'layout.md')) as f:
        for l in f:
            ls = l.strip()
            if ls == '':
                pass
            elif ls in ('posttitle.tex', 'title.tex', 'preamble.tex', 'header.tex'):
                pass # skip any that have been processed above
            elif ls.endswith('.html') or ls.endswith('.htm'):
                pass  # html files aren't latex-able
            elif ls.startswith('figures'):
                sectioninputs.append(get_figure_string(ls, localdir))
            else:
                sectioninputs.append(get_input_string(ls, localdir))
    sectioninputs = '\n'.join(sectioninputs)

    maintexstr = MAIN_TEMPLATE.format(**locals())

    #now save that string out as a file
    outname = outname if outname.endswith('.tex') else (outname + '.tex')
    outtexpath = os.path.join(builddir, outname)
    with open(outtexpath, 'w') as f:
        f.write(maintexstr)

    if outname.endswith('.tex'):
        outname = outname[:-4]

    if dobuild:
        #now actually run latex/bibtex
        args = [latex_exec, outname + '.tex']
        print('\n\RUNNING THIS COMMAND: "{0}"\n'.format(' '.join([latex_exec, outname + '.tex'])))
        subprocess.check_call(args, cwd=builddir)
        if dobibtex:
            args = [bibtex_exec, outname]
            print('\n\RUNNING THIS COMMAND: "{0}"\n'.format(' '.join([latex_exec, outname + '.tex'])))
            subprocess.check_call(args, cwd=builddir)
        for _ in range(npostbibcalls):
            args = [latex_exec, outname + '.tex']
            print('\n\RUNNING THIS COMMAND: "{0}"\n'.format(' '.join([latex_exec, outname + '.tex'])))
            subprocess.check_call(args, cwd=builddir)

        #launch the result if necessary
        resultfn = outtexpath[:-4] + ('.pdf' if 'pdf' in latex_exec else '.dvi')
        if openwith:
            args = openwith.split(' ')
            args.append(resultfn)
            print('\nLaunching as:' + str(args), '\n')
            subprocess.check_call(args)
        else:
            msg = '\nBuild completed.  You can see the result in "{0}": "{1}"'
            print(msg.format(builddir, resultfn), '\n')
    else:
        msg = 'Preprocessing done but skipping build.  Main file:"{0}.tex"'
        print(msg.format(os.path.join(builddir, outname)))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Local builder for authorea papers.')

    parser.add_argument('localdir', nargs='?', default='.',
                        help='The directory to actually search for the authorea'
                             ' files in. Default to the current directory.')
    parser.add_argument('--build-dir', '-d', default='authorea_build',
                        help='the directory to build the paper in')
    parser.add_argument('--latex', '-l', default='pdflatex',
                        help='The executable to use for the latex build step.')
    parser.add_argument('--bibtex', '-b', default='bibtex',
                        help='The executable to use for the bibtex build step.')
    parser.add_argument('--filename', '-f', default='authorea_paper',
                        help='The name to use for the output tex file.')
    parser.add_argument('--no-bibtex', action='store_false', dest='usebibtex',
                        help='Provide this to not run bibtex.')
    parser.add_argument('--no-title', action='store_false', dest='usetitle',
                        help='Provide this to skip the title command.')
    parser.add_argument('--title-input', action='store_true', dest='titleinput',
                        help='Provide this to have the title included via the '
                             '\\input command instead of directly in the '
                             'generated tex file. This is useful because \\input'
                             'sometimes prevents the title from being cased '
                             'correctly.', default=False)
    parser.add_argument('--n-runs-after-bibtex', '-n', type=int, default=3,
                        help='The number of times to call latex after bibtex.')
    parser.add_argument('--open-with', '-o', default=None,
                        help='An executable to launch the output file with. '
                             'Default is to not do anything with it.')
    parser.add_argument('--no-build', action='store_false', dest='dobuild',
                        help='Only do preprocessing and skip all the build/open steps')

    args = parser.parse_args()

    build_authorea_latex(args.localdir, args.build_dir, args.latex, args.bibtex,
                         args.filename, args.usetitle, args.usebibtex,
                         args.n_runs_after_bibtex, args.open_with,
                         args.titleinput, args.dobuild)
