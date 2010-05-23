babbisch-ooc
============

Generates flat (non-object-oriented) ooc bindings for C libraries.

Installation
------------

Currently, the best way to try babbisch-ooc is a virtualenv. You'll be able to update
your babbisch repositories very easily.

You need:
 - Python 2.6 (it might also work with Python 2.5)
 - `gccxml <http://gccxml.org>`_
 - `virtualenv <http://pypi.python.org/pypi/virtualenv>`_

First, install virtualenv::

    easy_install virtualenv

Then, create a virtualenv and activate it::

    virtualenv dev
    . dev/bin/activate

Inside this virtualenv, install the remaining Python dependencies:

 - `pyyaml <http://pyyaml.org>`_
 - `pygccxml <http://language-binding.net/>`_

Via this line::

    easy_install pyyaml pygccxml

Now, it's time to clone the git repositories and to install the software to
our virtualenv::

    git clone git://github.com/fredreichbier/babbisch-gccxml
    cd babbisch-gccxml
    python setup.py develop
    cd ../

    git clone git://github.com/fredreichbier/babbisch-ooc
    cd babbisch-ooc
    python setup.py develop

The reason we're using `develop` instead of `install` is: When you want to update
babbisch-gccxml or babbisch-ooc, you can just do a `git pull` in the repository with
no need to run `python setup.py develop` again.

Usage
-----

First, you need to generate a json interface from your C libraries via the babbisch-gccxml
tool. There is no ooc involved here, the generated json files just describe the functions
and types defined by your C library::

    babbisch-gccxml your-file.h -o your-file.json

You can also pass include paths to babbisch::

    babbisch-gccxml -I /usr/include/blah -I this/ your-file.h -o your-file.json

Now, to generate a ooc bindings file from that, you need to create an interface file for
the babbisch-ooc tool. It's in the yaml format, so let's call it `your-file.yaml`::

    Files:
	- your-file.json

You see, currently it only contains a list of json files. However, in the future it will contain
information on how to create the interface specifically.

Now, just run babbisch-ooc::

    babbisch-ooc your-file.yaml > your-file.ooc

And you might be able to use `your-file.ooc` without any manual work now.

.. warning:: Be sure not to call the ooc file like the main C header file. It will cause
	     include name clashes and much much fun.

Questions
---------

If you have any question, just join #ooc-lang on irc.freenode.net and hit fredreichbier with a crowbar.
