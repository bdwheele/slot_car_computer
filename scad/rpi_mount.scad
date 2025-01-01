use <../../hex_pattern.scad>

/* RPi Zero W mount box */
$fn = 128;

// test print used 1 as bot_thickness, wall_thickness, and lid_thickness.  pin_diameter=2.4

pin_diameter = 2.35;
pin_support = 5.5;
board_x = 30;
board_y = 65;
board_fudge = 0.5;
shell_height = 11;
bot_thickness = 1.5;
bot_clearance = 2;
wall_thickness = 1.5;
shell_mask = wall_thickness * 3;
lid_thickness = 1.5;
pcb_thickness = 1.4;



module pi_shell() {

    
    difference() {
        // outer casing
        hull() {
            for(x = [0, board_x + board_fudge]) {
                for(y = [0, board_y + board_fudge]) {
                    translate([x, y, 0]) cylinder(h=shell_height, r=wall_thickness);
                }
            }
        }        
        // board cavity
        translate([0, 0, bot_thickness]) cube([board_x + board_fudge, board_y + board_fudge, (shell_height + 1)]);
        
        // for all of the holes we're going to render them where they
        // belong relative to the board and then translate them all 
        // based on the fudging
        translate([board_fudge / 2, board_fudge /2, 0]) {
            // camera, 18mm
            translate([15 - (18/2), -(shell_mask/2), bot_thickness + bot_clearance]) cube([18, shell_mask, (shell_height + 1)]);
       
            // gpio header, 56mm clearance
            translate([board_x - (shell_mask/2), (board_y / 2) - (56 / 2), bot_thickness + bot_clearance]) cube([shell_mask, 56, (shell_height + 1)]);
            
            // sdcard, 13mm clearance
            translate([16.9 - (13 / 2), board_y -(shell_mask/2), bot_thickness + bot_clearance]) cube([13, shell_mask, (shell_height + 1)]);
            
            // hdmi, 11.5mm clearance
            translate([-(shell_mask/2), (board_y - 12.4) - 11.5 / 2, bot_thickness + bot_clearance]) cube([shell_mask, 11.5, (shell_height + 1)]); 
            // usb ports, 8mm clearance
            for(o = [41.4, 54]) {
                translate([-(shell_mask/2), (board_y - o) - (8 / 2), bot_thickness + bot_clearance]) cube([shell_mask, 8, (shell_height + 1)]);
            }
        }
    }
    // offset pins, all are 3.5mm from edges, hole is M2.5
    // as above, translate via the fudge.
    translate([board_fudge / 2, board_fudge /2, 0]) {
        for(x = [3.5, board_x - 3.5]) {
            for(y = [3.5, board_y - 3.5]) {
                translate([x, y, bot_thickness]) {
                    cylinder(d=pin_support, h=bot_clearance);
                    cylinder(d=pin_diameter, h=bot_clearance + pcb_thickness * 2);
                }
            }
        }
    }
}

module pi_lid(vents=false) {
    pin_height = shell_height - bot_thickness - bot_clearance - pcb_thickness;
    // create the lid body
    difference() {
        union() {
            hull() {
                for(x = [0, board_x + board_fudge]) {
                    for(y = [0, board_y + board_fudge]) {
                        translate([x, y, 0]) cylinder(h=lid_thickness, r=wall_thickness);
                    }
                }
            }             
            // features, translated from board-relative to fudged
            translate([board_fudge / 2, board_fudge /2, 0]) {        
                // support pins
                for(x = [3.5, board_x - 3.5]) {
                    for(y = [3.5, board_y - 3.5]) {
                        translate([x, y, 0.01 -pin_height]) {
                            difference() {
                                cylinder(d=pin_support, h=pin_height);
                                translate([0, 0, -0.1]) cylinder(d=pin_diameter + 0.1, h=1 + pin_height);
                            }
                        }
                    }
                }
                
                unfudge = board_fudge / 2 + wall_thickness;
                // camera, 18mm, 5mm 
                translate([15 - (17.5/2), -unfudge, -4.49]) cube([17.5, wall_thickness, 4.5]);
                       
                // sdcard, 13mm clearance, 4mm
                translate([16.9 - (12.5 / 2), board_y - wall_thickness + unfudge, -3.49]) cube([12.5, wall_thickness, 3.5]);
                
                // hdmi, 11.5mm clearance, 3mm
                translate([-unfudge, (board_y - 12.4) - 11 / 2, -2.49]) cube([wall_thickness, 11, 2.5]); 
                // usb ports, 8mm clearance, 4mm
                for(o = [41.4, 54]) {
                    translate([-unfudge, (board_y - o) - (7.5 / 2), -3.49]) cube([wall_thickness, 7.5, 3.5]);
                }
            }
        }
        translate([board_fudge / 2, board_fudge /2, 0]) {
            // gpio header, 56mm clearance, 7mm
            translate([board_x - board_fudge - 7, (board_y / 2) - (56 / 2), 0.5 -lid_thickness - pin_height]) cube([7 + board_fudge + 1 + wall_thickness, 56, lid_thickness + pin_height + 1.5]);
            // 5x2 notch 
            translate([board_x - board_fudge - 8.99, (board_y / 2) - (5 / 2), -0.5]) cube([2, 5, lid_thickness + 1]);
        }
    
        if(vents) {
            translate([board_x / 8 - 3, board_y/2 - 27, -0.5]) #hex_grid_mask(3, 10, 4, 1, lid_thickness + 1);
        }
        
    }    
}

pi_shell();

translate([0, 0, shell_height + 2]) pi_lid(true);
