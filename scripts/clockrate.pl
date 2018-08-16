#!/usr/bin/perl

# Usage: sudo nice -n -20 ./clockrate.pl
#
# Ensure that the host is running ntpd and has had plenty of time to
# stabilise. Then run this script and leave it for long enough to get
# a good r^2 value (0.99 or higher), and also for long enough to be
# confident that ntpd isn't about to change the frequency without us
# noticing.
#
# This script will run for many hours, but will eventually terminate
# after a fixed number of iterations. But you can also terminate it
# once you're satisfied that you have the result that you need.
#
# If the resulting ppm value is negative, decrease the crystal trim value.
# If the resulting ppm value is positive, increase the crystal trim value.

use Math::BigFloat;
use Time::HiRes qw( gettimeofday );
use Statistics::LineFit;

my $filename = '/sys/kernel/debug/regmap/spi0.0-sys_time/registers';

my $wrap = 0x10000000000;
my $topbyte = $wrap / 0x100;

my $iterations = 14400; # 8 hours or so

# This is the number of DW1000 clock ticks per microsecond.
my $scale = 63897.6;

# Flush after every print
$|=1;

sub decaclock {
    use bigint;

    open(my $fh, '<', $filename) or die "Could not open $filename\n";
    my $t = 0;
    while (<$fh>) {
        if (/: ([0-9a-fA-F]*)/) {
            $t = $t / 0x100;
            $t += hex($1) * $topbyte;
        }
    }
    close($fh);
    return $t;
}

sub display_data {
    my ($wall_array, $error_array, $fit) = @_;

    $fit->setData($wall_array, $error_array) or die "Invalid data";
    my ($intercept, $slope) = $fit->coefficients();
    my $ppm = $slope * 1000000;
    my $r_squared = $fit->rSquared();
    my $sigma = $fit->sigma();
    print "\x1b[2K\r";
    print "ppm: $ppm, r^2: $r_squared, sigma: $sigma";
}

sub collect {
    use bigint;

    ($wall_array, $deca_array, $error_array, $fit) = @_;
    my $olddeca = 0;
    my $wrapn = 0;

    my $zerowall = 0;
    my $zerodeca = 0;
    my $first = 1;
    
    for (my $i=0; $i < $iterations; $i++) {
        my ($s, $us) = gettimeofday;
        my $rawdeca = decaclock();
        my ($s2, $us2) = gettimeofday;
        my $wall = $s * 1000000 + $us;
        my $wall2 = $s2 * 1000000 + $us2;
        $wrapn++ if ($rawdeca < $olddeca);
        $olddeca = $rawdeca;
        my $deca = $rawdeca + $wrapn * $wrap;
        if ($first) {
            $first = 0;
            $zerowall = $wall;
            $zerodeca = $deca;
        }
        $walloffset = $wall - $zerowall;
        $decaoffset = $deca - $zerodeca;
        push @{$wall_array}, $walloffset->numify();
        push @{$deca_array}, $decaoffset;
        my $offset = $wall2 - $wall;

        my $wallf = Math::BigFloat->new($walloffset);
        my $decaf = Math::BigFloat->new($decaoffset);
        my $error = ($decaf / $scale) - $wallf;
        push @{$error_array}, $error->numify();
        my $errnum = $error->numify();
#        print "$walloffset : $decaoffset : $offset : $errnum\n";

        if ($i > 2) {
	    display_data($wall_array, $error_array, $fit);
        }

        sleep 2 unless ($i + 1) == $iterations;
    }
}

my @wall, @deca;
my @error;

my $fit = Statistics::LineFit->new();

collect(\@wall, \@deca, \@error, $fit);

print "\n";

