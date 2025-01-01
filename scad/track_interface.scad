// Create the track interface with the RPi0W and arducam
// NOTE:  the rpi doesn't /quite/ fit when printed on it's back.abs
use <rpi_mount.scad>
use <camera_mount.scad>


// track is 76.15mm wide, 7.1high


module upright() {
    translate([0, 0, 0]) {
        hull() {
            cube([7, 35, 7]);
            translate([0, 0, 120]) cube(7);
        }
    }

}

module overhead() {
    upright();
    translate([77, 0, 0]) upright();
    translate([77/2 - 5.25, 26 + 1.25, 126]) rotate([0, 0, -90]) camera_shell();
    translate([0, 0, 119]) cube([78, 7, 7]);
    translate([0, 1.5, 80]) rotate([0, 0, 90]) rotate([-90, 0, 0]) pi_shell();
}

/*
camera_shell();
translate([0, 0, 11]) camera_lid();

translate([0, 30, 0]) {
    pi_shell();
    translate([0, 0, 11 + 2]) pi_lid();
}
*/


overhead();