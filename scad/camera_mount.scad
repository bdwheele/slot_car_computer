



module camera_shell() {  
    // for an OV5647
    module support_peg() {
        // A support peg for the PCB.  Has a hole
        // for a M2 screw
        difference() {
            cylinder(h=5, d=4);
            cylinder(h=6, d=2);
        }
    }
   
    difference() {
        // make the outer casing
        hull() {
            for(x = [0, 26]) {
                for(y = [0, 25]) {
                    translate([x, y, 0]) cylinder(d=2.5, h=10);
                }
            }
        }
        // remove the middle
        translate([0, 0, 1]) cube([26, 25, 10]);
        // allow the cable to come out the back
        translate([4.5, -1.5, 8.01]) cube([17, 3 ,2]);
        // lens hole
        translate([12.5, 9.5, -1]) cylinder(d=8.5, h=3);
   }   
   
   // place the PCB support pegs
   translate([2.5, 9.5, 0]) {
       for(x = [0, 21]) {
           for(y = [0, 12.75]) {
               translate([x, y, 0]) support_peg();
           }
       }
   }   
   
}

module camera_lid() {
    difference() {
        // make the outer casing
        hull() {
            for(x = [0, 26]) {
                for(y = [0, 25]) {
                    translate([x, y, 0]) cylinder(d=2.5, h=1);
                }
            }
        }
   
       // place the holes
       translate([2.5, 9.5, 0]) {
           for(x = [0, 21]) {
               for(y = [0, 12.75]) {
                   translate([x, y, -0.1]) cylinder(d=3, h=4);
               }
           }
       }   
   }           
}


module lego_mount() {
    translate([7.8/2, 0, 0])
    rotate([0, 0, 90])
    difference() {
        cube([24, 7.8, 11]);
        for(i=[1:3]) {
            translate([8 * i - 4, 8.5, 7]) rotate([90, 0, 0]) cylinder(d=5, h=9);
        }
    }
}


$fn = 128;




camera_shell();
translate([0, 0, 11]) camera_lid();
translate([13, 0, 12]) lego_mount();