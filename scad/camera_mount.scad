
module camera_shell() {
    // make the outer casing
    hull() {
        for(x = [0, 
        cylinder(d=10, 
        
    }
}

module camera_lid() {
    
}




// size and spacing of PCB holes
hole_size = 2;
hole_x = 21;
hole_y = 12.75;


$fn = 128;

module pegs() {
    for(x = [0, hole_x]) {
        for(y = [0, hole_y]) {
            translate([x, y, 0]) cylinder(h=1, d=hole_size - 0.1);
        }
    }
}


module camera_mount() {
    translate([2.5, 2.5 , 2 - 0.01]) pegs();
    difference() {
        cube([hole_x + 5, hole_y + 5, 2]);
        translate([-0.01, 4, -0.5]) cube([20, 10, 3]);
    }
    
}


camera_mount();