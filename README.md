# Bodhi Scraper

## What is the need?
The [ostree](https://github.com/ostreedev/ostree-rs-ext) project has an implementation to create ["container native ostree"](https://github.com/coreos/enhancements/blob/main/os/coreos-layering.md#existing-work) functionality which has largely been the basis for ostree-rs-ext repo.
When a ostree commit from pristine CoreOS base image is encapsulated into an OCI container, the entire root filesystem is used to create a logical single chunk. This chunk translates into a single OCI layer.  

However, when the work for [ostree-layering](https://github.com/coreos/enhancements/blob/main/os/coreos-layering.md) started, the rpm-ostree commits could now have derived layers containing ```/etc``` files or third party daemons. This introduced new files that needed to be efficently kept taken care of when encapsulating a rpm-ostree commit.

Currently, ```rpm-ostree container encapsulate``` converts a commit into a OCI container. This works by: 


1) [rpm-ostree](https://github.com/coreos/rpm-ostree/blob/main/rust/src/container.rs#L213) getting metadata about the rpm packages installed in ostree commit and invoking ```ostree-rs-ext container encapsulate```. The metadata contains a list of all the files in the commit grouped by their RPM packages. The files that belong to no package have a special category "rpmostree_unpackaged_content". For brevity, I will refer to a single group of files which have the same RPM as "r_unit".
2) [ostree-rs-ext](https://github.com/ostreedev/ostree-rs-ext/blob/main/lib/src/container/encapsulate.rs#L173) divides the commit into several chunks with the help of the metadata from rpm-ostree. The [first chunk](https://github.com/ostreedev/ostree-rs-ext/blob/main/lib/src/chunking.rs#L206) contains the base pristing ostree commit and each of the [subsequent chunks](https://github.com/ostreedev/ostree-rs-ext/blob/main/lib/src/chunking.rs#L260) can and do  contain more than one r_unit. 
3) These chunks are then converted to layers of an OCI image


### Bin Packing Problem
When there exists a physical kernel limit on the number of layers an OCI image can have, and the number of RPMs are past that limit, we need to find a way to efficently combine RPMs into a single bin (layer). The hard limit set by the rpm-ostree maintainer is 64 layers. Currently, [basic_packing](https://github.com/ostreedev/ostree-rs-ext/blob/main/lib/src/chunking.rs#L396), sorts the r_units by descending size and takes all the RPMs past maximum and groups them by their Source RPMs (sRPMs). All these r_units grouped by their sRPMs are then all put into a single last bin. Hence we get 64 bins and solve our problem.


However, what we forgot here was the design constraint of reducing the delta's when pulling in the container image and unencapsulating it back into a rpm-ostree commit using ```rpm-ostree rebase $containerref```. The way we pack r_units into 64 bins will determing the time taken to pull or update a containe image. If a layer contains a RPM which is big in size and changes infrequently with a RPM that is small and changes frequently, then the entire bin will have to pulled again. 
So then what is the more intelligent way to pack the r_units into OCI layers?


## Solution (What does bodhi-scraper do?)
Utilizing the frequency of version update of a RPM to intelligently package chunks, the delta between container pulls can be minimized. There is an effort to compute the [change_time_offset](https://github.com/coreos/rpm-ostree/blob/815d038279720e265abfdaa72faeb5eb3d8be573/rust/src/container.rs#L291) of several RPM in the rpm database of a commit. However, this value is never actually used to pack chunks in a layer efficiently.
It is not only important to look at the frequency of version updates to current FCOS shipped RPM packages but also crucial to keep in mind that in the future more packages might get attached to FCOS and hence a metadata about their updates should also be taken into consideration.


Therefore, I have started a project, to web scrape all the stable RPM packages of current and upcoming releases and process them to give me metadata about RPM's frequency of update. This data in the future can be utilized by various rpm-ostree based OS (FOCS, RHCOS, Fedora Silverblue, Kinoite, IoT, RHEL 4 Edge) to intelligently package chunks into layers such that more frequently changing packages are kept separate from infrequently changing packages. The python script is hacky but I will keep making updates to make it better.

### Example of what the process_data() in scripts/scraper.py produces:
The JSON output contains a HashMap< String("Package Name" + "." + "Dist Tag"), Vec<{RPM Package with NEVRA and Metadata}>>
```
{
"packetdrill.f38": [
    {
      "build_time": "2022-12-05 19:58:15",
      "alias": "FEDORA-2022-49adbd8465",
      "name": "packetdrill-2.0~20220927gitc556afb-5.fc38"
    },
    {
      "build_time": "2022-12-05 17:28:24",
      "alias": "FEDORA-2022-fe8251c78b",
      "name": "packetdrill-2.0~20220927gitc556afb-4.fc38"
    }
  ],
  "python-py-algorand-sdk.f38": [
    {
      "build_time": "2022-12-05 19:49:26",
      "alias": "FEDORA-2022-f89892e4fa",
      "name": "python-py-algorand-sdk-1.20.2-1.fc38"
    }
  ],
 }
```
