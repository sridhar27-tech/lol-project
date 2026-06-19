const Createaproblematicfunction = () => {
const functions = [];

    for(var i =0 ; i<4;i++) {
    functions.push( () => {console.log(i)});
    }
    return functions;
}

const prob = Createaproblematicfunction();
console.log(prob[0]());

const Rightfunction = () => {
    const functions = [];

    for(var i =0 ; i<4;i++) {
  ((index) => {
        
            functions.push(()=> {console.log(index)});
        
    } )(i);
}

    return functions
}

const right = Rightfunction();
right[0]();
right[1]();
right[2]();
right[3]();