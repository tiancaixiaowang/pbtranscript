#!/usr/bin/env python

"""
Collapse redundant isoforms into transcripts, then merge transcripts
which have merge-able fuzzy junctions.

Input:
    0 - A FASTA/FASTQ/ContigSet file containing uncollapsed isoforms (hq_polished)
    1 - A SORTED GMAP SAM file containing alignments mapping uncollapsed
        isoforms to reference genomes (produced by map_isoforms_to_genome)
Output:
    0 - A GFF file containing good collapsed transcripts with fuzzy junctions merged.
"""
import sys
import logging
import argparse
import os.path as op

from pbcommand.cli.core import pbparser_runner
from pbcommand.models import FileTypes
from pbcommand.utils import setup_log

from pbtranscript.Utils import ln, as_contigset
from pbtranscript.io import parse_ds_filename
from pbtranscript.PBTranscriptOptions import get_base_contract_parser
from pbtranscript.collapsing.CollapseIsoforms import CollapseIsoformsRunner


log = logging.getLogger(__name__)


class Constants(object):
    """Constants used in tool contract."""
    TOOL_ID = "pbtranscript.tasks.collapse_mapped_isoforms"
    DRIVER_EXE = "python -m %s --resolved-tool-contract " % TOOL_ID
    PARSER_DESC = __doc__

    MIN_ALN_COVERAGE_ID = "pbtranscript.task_options.min_gmap_aln_coverage"
    MIN_ALN_COVERAGE_DEFAULT = 0.99
    MIN_ALN_COVERAGE_DESC = "Min query coverage to analyze a GMAP alignment (default: %s)" % MIN_ALN_COVERAGE_DEFAULT

    MIN_ALN_IDENTITY_ID = "pbtranscript.task_options.min_gmap_aln_identity"
    MIN_ALN_IDENTITY_DEFAULT = 0.95
    MIN_ALN_IDENTITY_DESC = "Min identity to analyze a GMAP alignment (default: %s)" % MIN_ALN_IDENTITY_DEFAULT

    MAX_FUZZY_JUNCTION_ID = "pbtranscript.task_options.max_fuzzy_junction"
    MAX_FUZZY_JUNCTION_DEFAULT = 5
    MAX_FUZZY_JUNCTION_DESC = "Max edit distance between merge-able fuzzy junctions (default: %s)" % MAX_FUZZY_JUNCTION_DEFAULT

    # Production isoseq always collapses consensus isoforms, not FLNC reads, default value must be 1
    MIN_FLNC_COVERAGE_DEFAULT = 1
    MIN_FLNC_COVERAGE_DESC = "Minimum number of supportive FLNC reads " + \
                             "only used for aligned FLNC reads, otherwise, result undefined (default: %s)" % MIN_FLNC_COVERAGE_DEFAULT

    ALLOW_EXTRA_5EXON_ID = "pbtranscript.task_options.allow_extra_5exon"
    ALLOW_EXTRA_5EXON_DEFAULT = False
    ALLOW_EXTRA_5EXON_DESC = "True: Collapse shorter 5' transcripts. " + \
                             "False: Don't collapse shorter 5' transcripts (default: %s)" % ALLOW_EXTRA_5EXON_DEFAULT

    SKIP_5_EXON_ALT_DEFAULT = False


def add_collapse_mapped_isoforms_io_arguments(arg_parser):
    """Add arguments for collapse isoforms."""
    helpstr = "Input uncollapsed isoforms in a FASTA, FASTQ or ContigSet file."
    arg_parser.add_argument("input_isoforms", type=str, help=helpstr)

    helpstr = "Input SORTED SAM file mapping uncollapsed isoforms to reference genome using GMAP."
    arg_parser.add_argument("sam_filename", type=str, help=helpstr)

    helpstr = "Output prefix, will write output files to " + \
              "<output_prefix>.fastq|.gff|.group.txt|.abundance.txt|.read_stat.txt"
    arg_parser.add_argument("output_prefix", type=str, help=helpstr)

    helpstr = "Output collapsed isoforms to a FASTA, FASTQ, or ContigSet file."
    arg_parser.add_argument("--collapsed_isoforms", type=str, default=None, help=helpstr)
    return arg_parser


def add_collapse_mapped_isoforms_arguments(arg_parser):
    """Add arguments for collapse isoforms."""
    coll_group = arg_parser.add_argument_group("Collapse isoforms arguments")
    coll_group.add_argument("-c", "--min_coverage", dest="min_aln_coverage",
                            default=Constants.MIN_ALN_COVERAGE_DEFAULT,
                            type=float, help=Constants.MIN_ALN_COVERAGE_DESC)

    coll_group.add_argument("-i", "--min_identity", dest="min_aln_identity",
                            default=Constants.MIN_ALN_IDENTITY_DEFAULT,
                            type=float, help=Constants.MIN_ALN_IDENTITY_DESC)

    coll_group.add_argument("--max_fuzzy_junction",
                            default=Constants.MAX_FUZZY_JUNCTION_DEFAULT,
                            type=int, help=Constants.MAX_FUZZY_JUNCTION_DESC)

    coll_group.add_argument("--flnc_coverage", dest="min_flnc_coverage", type=int,
                            default=Constants.MIN_FLNC_COVERAGE_DEFAULT,
                            help=Constants.MIN_FLNC_COVERAGE_DESC)

    coll_group.add_argument("--merge-5-shorter", dest="allow_extra_5exon",
                            default=Constants.ALLOW_EXTRA_5EXON_DEFAULT,
                            action="store_true", help=Constants.ALLOW_EXTRA_5EXON_DESC)

    #helpstr = "Skip alternative 5' exons."
    coll_group.add_argument("--skip_5_exon_alt", dest="skip_5_exon_alt",
                            default=Constants.SKIP_5_EXON_ALT_DEFAULT,
                            action="store_true", help=argparse.SUPPRESS)
    return arg_parser


def args_runner(args):
    """Run given input args"""
    c = CollapseIsoformsRunner(isoform_filename=args.input_isoforms,
                               sam_filename=args.sam_filename,
                               output_prefix=args.output_prefix,
                               min_aln_coverage=args.min_aln_coverage,
                               min_aln_identity=args.min_aln_identity,
                               min_flnc_coverage=args.min_flnc_coverage,
                               max_fuzzy_junction=args.max_fuzzy_junction,
                               allow_extra_5exon=args.allow_extra_5exon,
                               skip_5_exon_alt=args.skip_5_exon_alt)
    c.run()

    if args.collapsed_isoforms is not None:
        suffix = parse_ds_filename(args.collapsed_isoforms)[1]
        if op.exists(c.rep_fn(suffix)):
            ln(c.rep_fn(suffix), args.collapsed_isoforms)
        else:
            if suffix == ".contigset.xml": # make contigset from fasta
                as_contigset(c.rep_fn("fasta"), args.collapsed_isoforms)
            else:
                raise IOError("Could not make collapsed isoform file %s" % args.collapsed_isoforms)
    return 0


def resolved_tool_contract_runner(rtc):
    """Run given a resolved tool contract"""
    raise NotImplementedError() # Merged to post_mapping_to_genome
#    c = CollapseIsoformsRunner(isoform_filename=rtc.task.input_files[0],
#                               sam_filename=rtc.task.input_files[1],
#                               collapsed_isoform_filename=rtc.task.output_files[0],
#                               min_aln_coverage=rtc.task_options.min_aln_coverage,
#                               min_aln_identity=rtc.task_options.min_aln_identity,
#                               max_fuzzy_function=rtc.task_options.max_fuzzy_function,
#                               allow_extra_5exon=rtc.task_options.allow_extra_5exon)
#    c.run()
#    ln(c.good_gff_fn, rtc.task.output_files[1])
#    ln(c.group_fn, rtc.task.output_files[2])
#    return 0


def add_collapse_mapped_isoforms_tcp_options(tcp):
    """Add tcp options"""
    tcp.add_int(option_id=Constants.MAX_FUZZY_JUNCTION_ID, option_str="max_fuzzy_junction",
                name="max fuzzy junction", default=Constants.MAX_FUZZY_JUNCTION_DEFAULT,
                description=Constants.MAX_FUZZY_JUNCTION_DESC)

    tcp.add_float(option_id=Constants.MIN_ALN_COVERAGE_ID, option_str="min_aln_coverage",
                  name="min gmap aln coverage", default=Constants.MIN_ALN_COVERAGE_DEFAULT,
                  description=Constants.MIN_ALN_COVERAGE_DESC)

    tcp.add_float(option_id=Constants.MIN_ALN_IDENTITY_ID, option_str="min_aln_identity",
                  name="min gmap aln identity", default=Constants.MIN_ALN_IDENTITY_DEFAULT,
                  description=Constants.MIN_ALN_IDENTITY_DESC)

    tcp.add_boolean(option_id=Constants.ALLOW_EXTRA_5EXON_ID, option_str="allow_extra_5exon",
                    name="allow extra 5exon", default=Constants.ALLOW_EXTRA_5EXON_DEFAULT,
                    description=Constants.ALLOW_EXTRA_5EXON_DESC)
    return tcp


def get_contract_parser():
    """Get tool contract parser.
    Input:
        idx 0 -
    Output:
        idx 0 - reads which can represent collapsed isoforms in CONTIGSET
        idx 1 - collapsed isoforms in GFF
        idx 2 - collapsed isoform groups in TXT
    """
    p = get_base_contract_parser(Constants, default_level="DEBUG")

    # argument parser
    add_collapse_mapped_isoforms_io_arguments(p.arg_parser.parser)
    add_collapse_mapped_isoforms_arguments(p.arg_parser.parser)

    # tool contract parser
    tcp = p.tool_contract_parser
    tcp.add_input_file_type(FileTypes.DS_CONTIG, "hq_isoforms_ds", "ContigSet In",
                            "Input HQ polished isoforms in ContigSet file") # input 0
    tcp.add_input_file_type(FileTypes.SAM, "sorted_gmap_sam", "SAM In",
                            "Sorted GMAP SAM file") # input 1
    tcp.add_output_file_type(FileTypes.DS_CONTIG, "collapsed_isoforms_rep_ds",
                             name="Collapsed isoforms",
                             description="Representative reads of collapsed isoforms",
                             default_name="output") # output 0
    tcp.add_output_file_type(FileTypes.GFF, "collapsed_isoforms_gff",
                             name="Collapsed isoforms GFF",
                             description="Collapsed isoforms gff",
                             default_name="output") # output 1
    tcp.add_output_file_type(FileTypes.TXT, "groups_txt",
                             name="TXT file",
                             description="Collapsed isoform groups",
                             default_name="output_groups") # output 2

    add_collapse_mapped_isoforms_tcp_options(tcp)
    return p


def main(args=sys.argv[1:]):
    """Main"""
    return pbparser_runner(argv=args,
                           parser=get_contract_parser(),
                           args_runner_func=args_runner,
                           contract_runner_func=resolved_tool_contract_runner,
                           alog=log,
                           setup_log_func=setup_log)


if __name__ == "__main__":
    sys.exit(main())
