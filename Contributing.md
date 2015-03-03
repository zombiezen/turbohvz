# Getting the source #

You will need to have [Subversion](http://subversion.tigris.org/) installed on your computer in order to develop TurboHvZ.  After you have installed it, consult [the instructions in the source tab](http://code.google.com/p/turbohvz/source/checkout).

# Making changes #

After you have your working copy, make the changes you want, but make sure you update your working copy to get the latest source code.

## Guidelines ##

Since TurboHvZ is a relatively small project, there are not many strict policies on what must go in a branch and what doesn't have to, but there are a few rough guidelines the project should follow.  Generally:

  * The trunk _must_ pass all unit tests (run ` python setup.py test `)
  * The trunk _should be_ mostly usable
  * Each minor version (versions are: 

&lt;major&gt;

.

&lt;minor&gt;

.

&lt;patch&gt;

) should have its own branch
  * Each patch release should be tagged

## Committing your changes ##

**If you are a project member**: Commit your working copy and your changes will be made to the source code immediately.

**If you are not a project member**: Email your changes as the output from ` svn diff ` to [rlight2@gmail.com](mailto:rlight2@gmail.com) with the subject line ` TurboHvZ PATCH: [brief description] `

# Releasing a version #

If you are one of the project maintainers and you think the code is ready for release, then you must follow one of the following procedures:

## Major/Minor release ##

  1. Make a new branch from the trunk called 

&lt;major&gt;

.

&lt;minor&gt;


  1. Tag the branch as 

&lt;major&gt;

.

&lt;minor&gt;

.0
  1. From the tagged working copy, run the following commands:
```
  python setup.py sdist --formats=gztar,bztar,zip
  python setup.py bdist_egg
```
  1. [Upload the files](http://code.google.com/p/turbohvz/downloads/entry) from the dist directory
  1. Bump the version number in the trunk to the next minor release ([hvz/release.py](http://turbohvz.googlecode.com/svn/trunk/hvz/release.py))

## Patch release ##

  1. Bump the version number in the branch to the next patch release ([hvz/release.py](http://turbohvz.googlecode.com/svn/trunk/hvz/release.py))
  1. Tag the version branch as 

&lt;major&gt;

.

&lt;minor&gt;

.0
  1. From the tagged working copy, run the following commands:
```
  python setup.py sdist --formats=gztar,bztar,zip
  python setup.py bdist_egg
```
  1. [Upload the files](http://code.google.com/p/turbohvz/downloads/entry) from the dist directory