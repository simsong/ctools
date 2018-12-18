# ctools

A collection of utility programs for working with paths, Amazon S3, and Spark

## Usage
Typically, this repository will be a submodule in another project. C++ projects will include the files in src/ in their program and manually write a DFXML file using the primitive XML writing tools that are included.
These tools are not guarenteed to create clean XML, but they can handle XML of any size.

Sometimes when working with a submodule, you may get off the master and end up with a disconnected head. If so, use this to get back on the master:

```
$ git checkout -b newbranch; git checkout master; git merge newbranch; git branch -d newbranch
```

