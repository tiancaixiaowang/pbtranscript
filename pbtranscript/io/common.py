#!/usr/bin/env python

"""Define common classes."""

import os.path as op

__all__ = ["ClusterName",
           "parse_ds_filename",
           "SampleIsoformName"]


def parse_ds_filename(fn):
    """Parse a read file in FASTA/FASTQ/CongitSet format, return
    (file_prefix, file_suffix).
    """
    if fn.endswith(".contigset.xml"):
        prefix = op.join(op.dirname(fn), '.'.join(op.basename(fn).split('.')[0:-2]))
        suffix = "contigset.xml"
    else:
        prefix = op.join(op.dirname(fn), '.'.join(op.basename(fn).split('.')[0:-1]))
        if fn.endswith(".fasta") or fn.endswith(".fa"):
            suffix = "fasta"
        elif fn.endswith(".fastq") or fn.endswith(".fq"):
            suffix = "fastq"
        else:
            raise ValueError("Invalide FASTA/FASTQ/ContigSet file %s" % fn)
    return (prefix, suffix)


class ClusterName(object):

    """
    Cluster Name e.g., c72/f2p14/1556
    """
    def __init__(self, cluster_id, num_fl, num_nfl, length):
        """
        Parameters:
            cluster_id can either be a string, or a int
            e.g., 'c12', '12' or 12.
        """
        self.cluster_id_str = None
        if isinstance(cluster_id, str):
            if cluster_id.startswith('c'):
                self.cluster_id_str = cluster_id
            else:
                self.cluster_id_str = 'c' + cluster_id
        elif isinstance(cluster_id, int):
            self.cluster_id_str = 'c{index}'.format(index=cluster_id)
        if self.cluster_id_str is None:
            raise ValueError("Invalid cluster id %s" % cluster_id)

        self.num_fl = int(num_fl)
        self.num_nfl = int(num_nfl)
        self.length = int(length)

    @property
    def cluster_id_num(self):
        """return cluster_id_num as int"""
        assert self.cluster_id_str.startswith('c')
        return int(self.cluster_id_str[1:])

    def __str__(self):
        return "{cid}/f{num_fl}p{num_nfl}/{length}".format(
            cid=self.cluster_id_str, num_fl=self.num_fl,
            num_nfl=self.num_nfl, length=self.length)

    @classmethod
    def fromString(cls, line):
        """
        Returns a ClusterName object from a line.
        """
        try:
            cluster_id_str, f_p, length = line.split('/')
            f, p = f_p.split('p')
            num_fl, num_nfl = int(f[1:]), int(p)
            return ClusterName(cluster_id=cluster_id_str,
                               num_fl=num_fl, num_nfl=num_nfl, length=length)
        except (ValueError, IndexError):
            raise ValueError("Invalid ClusterName %s, should be " % line +
                             "c<cluster_index>/f<num_fl>p<num_nfl>/<length>")


class SampleIsoformName(ClusterName):

    """Isoform Name with sample prefix

    e.g., i1_HQ_sample18ba5d|c72/f2p14/1556
    """

    def __init__(self, sample_prefix, cluster_id, num_fl, num_nfl, length):
        self.sample_prefix = sample_prefix
        super(SampleIsoformName, self).__init__(cluster_id=cluster_id, num_fl=num_fl,
                                                num_nfl=num_nfl, length=length)

    @classmethod
    def fromString(cls, line):
        """Returns a SampleIsoformName object."""
        try:
            sample_prefix, cluster_name = line.strip().split('|')
            c = ClusterName.fromString(cluster_name)
            return SampleIsoformName(sample_prefix=sample_prefix, cluster_id=c.cluster_id_str,
                                     num_fl=c.num_fl, num_nfl=c.num_nfl, length=c.length)
        except (ValueError, IndexError):
            raise ValueError("Invalid SampleIsoformName %s, should be " % line +
                             "<sample_prefix>|c<cluster_index>/f<num_fl>p<num_nfl>/<length>")
