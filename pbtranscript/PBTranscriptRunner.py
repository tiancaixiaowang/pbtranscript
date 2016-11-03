#!/usr/bin/env python
###############################################################################
# Copyright (c) 2011-2013, Pacific Biosciences of California, Inc.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of Pacific Biosciences nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# NO EXPRESS OR IMPLIED LICENSES TO ANY PARTY'S PATENT RIGHTS ARE GRANTED BY
# THIS LICENSE.  THIS SOFTWARE IS PROVIDED BY PACIFIC BIOSCIENCES AND ITS
# CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT
# NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL PACIFIC BIOSCIENCES OR
# ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

"""This script defines class PBTranscript."""
import sys
import logging

from pbcommand.cli import pacbio_args_runner
from pbcommand.utils import setup_log
from pbcore.util.ToolRunner import PBMultiToolRunner

from pbtranscript.PBTranscriptException import PBTranscriptException
from pbtranscript.Classifier import Classifier, ChimeraDetectionOptions
from pbtranscript.ClusterOptions import IceOptions, SgeOptions, \
    IceQuiverHQLQOptions
from pbtranscript.Cluster import Cluster
from pbtranscript.SubsetExtractor import ReadsSubsetExtractor, \
    SubsetRules
from pbtranscript.PBTranscriptOptions import get_argument_parser
from pbtranscript.__init__ import get_version


log = logging.getLogger(__name__)


# FIXME(nechols)(2016-03-03): this is increasingly divergent from the parent
# class - we should just detach it altogether
class PBTranscript(PBMultiToolRunner):

    """
    Class PBTranscript defines tool kits for cDNA analysis, including
    `classify` and `cluster`.
    `classify` - pbtranscript classifies reads from a fasta/q file.
    For each read, identify whether it is full length, whether 5', 3' and
    poly A tail have been found. The input fasta/q file is usually generated
    from RS_ReadsOfInsert protocol (e.g., reads_of_insert.fasta/q).
    `cluster` -  pbtranscript calls the ICE algorithm, which stands for
    'Iteratively Clustering and Error correction' to identify de novo
    consensus isoforms.
    """

    def __init__(self, args, subCommand=None):
        assert subCommand in [None, "classify", "cluster", "subset"]
        self.args = args
        self._subCommand = subCommand
        if subCommand is None:
            self._subCommand = self.args.subCommand
        super(PBTranscript, self).__init__(self.__doc__)

    def _setupLogging(self):
        pass

    def _setupParsers(self, description):
        pass

    def _addStandardArguments(self):
        pass

    def _parseArgs(self):
        pass

    def getVersion(self):
        return get_version()

    def run(self):
        """Run classify, cluster, polish or subset."""
        cmd = self._subCommand
        try:
            if cmd == 'classify':
                opts = ChimeraDetectionOptions(
                    min_seq_len=self.args.min_seq_len,
                    min_score=self.args.min_score,
                    min_dist_from_end=self.args.min_dist_from_end,
                    max_adjacent_hit_dist=self.args.max_adjacent_hit_dist,
                    primer_search_window=self.args.primer_search_window,
                    detect_chimera_nfl=self.args.detect_chimera_nfl)

                obj = Classifier(reads_fn=self.args.readsFN,
                                 out_dir=self.args.outDir,
                                 out_reads_fn=self.args.outReadsFN,
                                 primer_fn=self.args.primerFN,
                                 primer_report_fn=self.args.primerReportFN,
                                 summary_fn=self.args.summary_fn,
                                 cpus=self.args.cpus,
                                 change_read_id=True,
                                 opts=opts,
                                 out_flnc_fn=self.args.flnc_fa,
                                 out_nfl_fn=self.args.nfl_fa,
                                 ignore_polyA=self.args.ignore_polyA,
                                 reuse_dom=self.args.reuse_dom,
                                 ignore_empty_output=self.args.ignore_empty_output)
                obj.run()
            elif cmd == 'cluster':
                ice_opts = IceOptions(quiver=self.args.quiver,
                                      use_finer_qv=self.args.use_finer_qv,
                                      targeted_isoseq=self.args.targeted_isoseq,
                                      flnc_reads_per_split=self.args.flnc_reads_per_split,
                                      nfl_reads_per_split=self.args.nfl_reads_per_split,
                                      num_clusters_per_bin=self.args.num_clusters_per_bin)
                sge_opts = SgeOptions(unique_id=self.args.unique_id,
                                      use_sge=self.args.use_sge,
                                      max_sge_jobs=self.args.max_sge_jobs,
                                      blasr_nproc=self.args.blasr_nproc,
                                      quiver_nproc=self.args.quiver_nproc,
                                      sge_queue=self.args.sge_queue,
                                      sge_env_name=self.args.sge_env_name)

                ipq_opts = IceQuiverHQLQOptions(qv_trim_5=self.args.qv_trim_5,
                                                qv_trim_3=self.args.qv_trim_3,
                                                hq_quiver_min_accuracy=self.args.hq_quiver_min_accuracy,
                                                hq_isoforms_fa=self.args.hq_isoforms_fa,
                                                hq_isoforms_fq=self.args.hq_isoforms_fq,
                                                lq_isoforms_fa=self.args.lq_isoforms_fa,
                                                lq_isoforms_fq=self.args.lq_isoforms_fq)

                obj = Cluster(root_dir=self.args.root_dir,
                              flnc_fa=self.args.flnc_fa,
                              nfl_fa=self.args.nfl_fa,
                              bas_fofn=self.args.bas_fofn,
                              ccs_fofn=self.args.ccs_fofn,
                              out_fa=self.args.consensusFa,
                              sge_opts=sge_opts,
                              ice_opts=ice_opts,
                              ipq_opts=ipq_opts,
                              report_fn=self.args.report_fn,
                              summary_fn=self.args.summary_fn,
                              output_pickle_file=self.args.pickle_fn,
                              tmp_dir=self.args.tmp_dir)
                obj.run()

            elif cmd == 'subset':
                rules = SubsetRules(FL=self.args.FL,
                                    nonChimeric=self.args.nonChimeric)

                obj = ReadsSubsetExtractor(inFN=self.args.readsFN,
                                           outFN=self.args.outFN,
                                           rules=rules,
                                           ignore_polyA=self.args.ignore_polyA,
                                           printReadLengthOnly=self.args.printReadLengthOnly)
                obj.run()
            else:
                raise PBTranscriptException(cmd,
                                            "Unknown command passed to pbtranscript:"
                                            + self.args.subName)
        except Exception:
            logging.exception("Exiting pbtranscript with return code 1.")
            return 1
        return 0

def args_runner(args):
    return PBTranscript(args).start()

def main(argv=sys.argv):
    mp = get_argument_parser()
    return pacbio_args_runner(
        argv=argv[1:],
        parser=mp,
        args_runner_func=args_runner,
        alog=log,
        setup_log_func=setup_log)

if __name__ == "__main__":
    sys.exit(main())
