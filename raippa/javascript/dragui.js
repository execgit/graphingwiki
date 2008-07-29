/* Script dragui.js
 *  A drag&drop user interface to create course/task.
 *  Requires mootools v1.2 with Drag.Move and moocanvas extensions
 */


/* Initializing some values after page is ready. boxData includes data of 
 * boxes structured in following way:
 * <id>         : box value
 * <id>_type    : random | select
 * <id>_wrong   : where to go after a wrong answer
 * <id>_require : boxes that need to be completed before continuing
 * lkm          : count of boxes created
 * endPoints    : list of boxes without child
 */
window.addEvent('domready', function(){
 childBoxes = new Hash();
 boxData = new Hash({
     'lkm': 1,
     'endPoints': new Array()
     });

$$('#b0').each(function(drag){  

    childBoxes.set(drag.id, new Array());
    drag.makeDraggable({
        onDrag: function(){
           drawline(); 
           }
        });
	drag.setStyles({
		'background-color' :'#6495ED',
		'cursor' : 'move',
		'text-align' : 'center',
		'left' : '550px',
		'top': '150px',
		'widht': '150px',
		'height': '50px'
		});
    });

/* Making all course items draggable*/
$$('.dragItem').each(function(item){
    item.addEvent('mousedown', function(e){
        var oldColor = new Array(2);
        var drop =  $$('div[id^=b]');
        var e = new Event(e).stop();
        var input = this.getChildren('input')
		var value = input.get('value');
		var description = input.get('name');
        var clone = this.clone()
            .setStyles(this.getCoordinates())
            .setStyles({'opacity' : 0.7})
            .addEvent('emptydrop', function(){
                this.destroy();
            }).inject(document.body);
            clone.id = "clone";
       var drag = clone.makeDraggable({
            droppables :[drop],

            onDrag: function(element){
            element.setOpacity(0.7);
            },

            onDrop: function(element, droppable){
                element.destroy();
                if(droppable){
                droppable.morph({
                    'background-color' : oldColor[1],
                    'height' : 50,
                    'width' : 150/*,
                    'border': '0px solid #33cc33'*/
                });
                    if(childBoxes.get(droppable.id).length ==0){
                    newBox(droppable.id, value, description);
                    setTimeout("drawline()", 500);
                    setTimeout("drawline()", 400);
                    setTimeout("drawline()", 200);
                    }else{
                        createMenu(droppable, value, description);
                    }
                }
            },
            onEnter: function(el, drop){
                         if(oldColor[0]!=drop.id){
                         oldColor[1] = drop.getStyle('backgroundColor');
                         oldColor[0]= drop.id;
                         }
                    drop.morph({
                    'background-color' : '#003366',
                    'height' : 60,
                    'width' : 170/*,
                    'border' : '5px solid #000'*/
                });
            },
            onLeave : function(el, drop){
                drop.morph({
                    'background-color' : oldColor[1],
                    'height' : 50,
                    'width' : 150 /*,
                    'border': '0px solid #33CC33'*/
                });
          }
        });
        drag.start(e);
    });
    item.addEvent('click',function(){
        $('clone').destroy();
        });
	item.setStyles({
	'margin-bottom' :'3px',
	'background-color' : '#E7E7E7',
	'cursor' : 'move',
	'z-index': '1'
		});


	});
var canvDiv = new Element('div',{
	'styles' :{
		'position':'absolute',
		'z-index' : '0'
	}
});
canvDiv.set('left', 0);
canvDiv.set('top' , 0);
	//$(document.body).grab(canvDiv.grab(canv),'top');
try{
loadData();
}catch(E){}

drawline();
});//domready


/* Draws lines between all boxes and endpoints */
function drawline(id){
if(id != null){
var boxes = [$(id)];
}else{
var boxes = $(document.body).getElements('div[id^=b]');
$$('canvas[id^=canv]').destroy();
}
var coords = new Array();
var canvHeight = 0;
var canvWidth = 0;
for(var i=0;  i < boxes.length; i++){
 c1 = boxes[i].getCoordinates();
pId = boxes[i].id;
 c1y = c1.top + c1.height / 2;
 c1x = c1.left + c1.width / 2;
 var childs = childBoxes.get(pId);
if(childs === null || childs.length < 1){
    if(boxData.get('endPoints').contains(pId)){
    childs = ['ep_'+ boxes[i].id];
    }else{
        continue;
    }
}
if(id != null){
childs.combine(getParentBox(id));
}
for(var j = 0 ; j < childs.length ; j++){
 c2 = $(childs[j]).getCoordinates($(pId));
 c2a = $(childs[j]).getCoordinates();
 c2y = c2a.top + 0.5 * c2a.height;
 c2x = c2a.left + 0.5 * c2a.width;

 if(boxData.get(pId+'_wrong') == $(childs[j]).id){
color = '#FF0000';
 }else if(boxData.get(pId+'_type') == 'select'){
color = '#00FF00';
 }else if(boxData.get(pId+'_type') == 'random'){
color = '#0000FF';
 }else{
color = '#000000';
 }


if($('canv_'+childs[j]+'_'+pId) != null){
	$('canv_'+childs[j]+'_'+pId).destroy();
}
if($('canv_'+ pId+'_'+childs[j]) != null){
	canv = $('canv_'+ pId+'_'+childs[j]);
}else{
	canv = new Canvas({
		'id': 'canv_'+ pId+'_'+childs[j],
		'styles' : {
			'position' : 'absolute'
			}
	});
	}
	xdiff = Math.max(Math.abs(c1.width/2 + c1.left - c2a.width / 2-c2a.left),4);
	ydiff = Math.max(Math.abs(c1.height/2 + c1.top - c2a.height / 2-c2a.top),4);
	
	canv.setStyle('top' , Math.min(c1y,c2y) - 2);
	canv.setStyle('left',  Math.min(c1x, c2x)- 2);

	canv.height = ydiff + 4;
	canv.width = xdiff+4;
	yswap = 0;

	if((c2y - c1y) * (c2x - c1x) < 0){
	yswap = 1;
	}

	$(document.body).grab(canv,'top');
	ctx = canv.getContext('2d');
	ctx.lineWidth = 4;
	ctx.beginPath();
	ctx.stroStyle = color;
	ctx.moveTo(2, ydiff * yswap +2 - yswap * 4);
	ctx.lineTo(xdiff - 2, ydiff * Math.abs(yswap -1) -2 + yswap * 4);
	ctx.stroke();
}
}

}

/* Returns parents of given object */
function getParentBox(id){
var result = new Array();
childBoxes.each(function(value, key){
    if(value.contains(id)){
        result.include(key);
    }
});
return result.flatten();
}


/* Returns all child nodes of given object */
function getChildBox(id){
var childs = childBoxes.get(id);
var result = new Array();
var tmp = new Array();
while(childs.length != 0){
result.combine(childs);
tmp.empty();

childs.each(function(el){
tmp.combine(childBoxes.get(el)); 
        });
childs = tmp.flatten();
}
return result.flatten();
}

/* Creates menu to edit box*/
function editMenu(button){
try{
    $('boxMenu').destroy();
}catch(e){}
    var pDiv = $(button).parentNode;
    var menu = new Element('div', {
    'id' : 'boxMenu',
    'styles' :{
        'position' : 'absolute',
        'text-align' : 'center',
        'width' : 100,
        'height' : 50,
        'background' : '#caffee',
        'z-index' : 5,
        'top' : button.getPosition().y,
        'left' : button.getPosition().x,
        'opacity' : 0.7
            }
    });
menu.addEvents({
    mouseenter: function(){
        this.morph({
                'opacity': 1,
                'height': 100,
                'width' : 100
            });
        },
    mouseleave : function(){
        this.morph({
                'height' : 80,
                'width' : 100,
                'opacity' : 0.9
            });
        }
    });
var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }

        });

var detach = new Element('input', {
        'type' : 'button',
        'value' : 'Detach',
        'events' : {'click': function(){
                childBoxes.get(pDiv.id).empty();
                newEndPoint(pDiv);
                menu.destroy();
        }}
});
var type = new Element('input');
var del = new Element('input', {
'type' : 'button',
'value' : 'Delete box',
'events' : {'click' : function(){
if(confirm('Delete box?')){
deleteBox(pDiv);
}
menu.destroy();
        }
    }
});

var reqMenu  = new Element('input', {
'type' : 'button',
'value' : 'Prerequisites',
'events' : { 'click' : function(){
dropMenu(pDiv);
menu.destroy();
        }
    }
});

cancel.inject(menu);
menu.grab(new Element('br'));
del.inject(menu);
if(getParentBox(pDiv.id).length > 1){
reqMenu.inject(menu);
}
if(childBoxes.get(pDiv.id).length == 1){
    if(getParentBox(childBoxes.get(pDiv.id).getLast()).length > 1){
        detach.inject(menu);
    }
}
menu.inject(document.body);
//menu.fireevent('mouseenter');
}


/* Menu that gives chace to select what to do when box allready has one or
   more childs. Posible actions: replace old box or add new one to tree*/
function createMenu(pDiv, value, desc){
var pDiv = $(pDiv);
    var menu = new Element('div', {
    'id' : 'boxMenu',
    'styles' :{
        'position' : 'absolute',
        'text-align' : 'center',
        'border' : '2px solid black',
        'width' : 160,
        'background' : '#caffee',
        'z-index' : 5,
        'top' : pDiv.getPosition().y,
        'left' : pDiv.getPosition().x
            }
    });

var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }

        });

var replBut = new Element('input', {
        'type': 'button',
        'value' : 'Replace',
        'events' : {'click' : function(){
        pDiv.childNodes[0].nodeValue = 'value : ' + value;
        menu.destroy();
        }}
 });

var randomRadio = new Element('input', {
        'type' : 'radio',
        'id' : 'rradio',
        'name' : 'typeSelect',
        'value' : 'random',
        'title' : 'Randomly selected'
        });

var selectRadio = new Element('input', {
        'type' : 'radio',
        'id' : 'sradio',
        'name' : 'typeSelect',
        'value' : 'select',
        'title' : 'Selectable',
        'checked': 'checked'
        });
var wrongRadio = new Element('input', {
        'type' : 'radio',
        'id' : 'wradio',
        'name' : 'typeSelect',
        'value' : 'wrong',
        'title' : 'After wrong answer'
        });


var newBut = new Element('input', {
        'type': 'button',
        'value' : 'New Box',
        'events' : {'click' : function(){
        var type = menu.getElements('input[name=typeSelect]');
        type = type.filter(function(el){
            return el.checked;
            }).get('value');
        newBox(pDiv.id, value, desc, type);
        menu.destroy();
        }}

});
var insAfter = new Element('input', {
        'type' : 'button',
        'value' : 'Insert after',
        'events' : {'click': function(){
        newBox(pDiv.id, value, desc,'after');
        menu.destroy();
        }}
});

var radioTab = new Element('tbody');
cancel.inject(menu);
menu.grab(new Element('br'));
radioTab.grab(new Element('tr').adopt(
                new Element('td').grab(selectRadio), 
                new Element('td').grab(new Element('label', {
                'for' : 'sradio',
                'text' :'Selectable'
            }))));

radioTab.grab(new Element('tr').adopt(
                new Element('td').grab(randomRadio), 
                new Element('td').grab(new Element('label', {
                'for' : 'rradio',
                'text' :'Random',
				'title' : 'Randomly Selected'
            }))));

/*
radioTab.grab(new Element('tr').adopt(
                new Element('td').grab(wrongRadio), 
                new Element('td').grab(new Element('label', {
                'for' : 'wradio',
                'text' :'After wrong answer'
            }))));
*/
menu.grab(new Element('table').grab(radioTab));
menu.getElements('tr, td').setStyles({'border':'none'})
//menu.getElements('td').setStyle('border','none'})
menu.getElements('table').setStyles({'border':'none', 'margin':'0'})

newBut.inject(menu);
    menu.adopt(new Element('br'), new Element('hr'));
replBut.inject(menu);
if(childBoxes.get(pDiv.id).length == 1){
menu.adopt(new Element('br'), insAfter);
}
menu.inject(document.body);
}


/*Deletes given element and corrects child relations. Checks also 
 if corrections in end points are needed*/
function deleteBox(pDiv){
var pDiv = $(pDiv);
getChildBox(pDiv.id).each(function(id){
if(boxData.get('endPoints').contains(id)){
     ep = $('ep_'+id);
     ep.setStyle('top', Math.max(ep.getPosition().y - 75, 17));
}
el = $(id);
pos = Math.max(el.getPosition().y -75, 100);
el.setStyle('top', pos);

        });
boxData.erase(pDiv.id);
childBoxes.each(function(value, key){
/* Inserting child data to parent*/
if(value.contains(pDiv.id)){
    value.erase(pDiv.id);
    value.extend(childBoxes.get(pDiv.id));

    if(value.length<1){
        boxData.get('endPoints').include(key);
        newEndPoint($(key));
    }
}
});
if(boxData.get('endPoints').contains(pDiv.id)){
    $('ep_'+pDiv.id).destroy();
}
childBoxes.erase(pDiv.id);
pDiv.destroy();
drawline();
}


/* Deletes whole child tree of given element*/
function deleteTree(){
var pDiv = $(pDiv);
//TODO: delete every child box
pDiv.destroy();
drawline();
}


/* Creates new endpoint to specified box */
function newEndPoint(pDiv){
var pDiv = $(pDiv);
boxData.get('endPoints').include(pDiv.id);

var ep = new Canvas({
    'id' : 'ep_'+ pDiv.id,
    'title' : 'End point',
    'styles' : {'position': 'absolute',
                'cursor': 'move',
                'z-index' : 1,
                'left': pDiv.getPosition().x + pDiv.getCoordinates().width /2 -10,
                'top': pDiv.getPosition().y + 75
                } 
});
ep.inject(document.body);

ep.height = 20;
ep.width = 20;
var ctx = ep.getContext('2d');
ctx.fillStyle = "#ff0000";
ctx.beginPath();
ctx.arc(10,10,10,0,Math.PI*2, false);
ctx.fill();


ep.addEvent('mousedown', function(e){
    var e = new Event(e).stop();
    var drops =  $$('div[id^=b]');
    var drag = ep.makeDraggable({
        droppables : [drops],
        onDrag: function(){
            drawline(pDiv.id);
        },
        onDrop: function(el, drop){
            if(drop){
                var p_id = el.id.replace('ep_','');
                childBoxes.get(p_id).include(drop.id);
                boxData.get('endPoints').erase(p_id);
                el.destroy();
                drawline();
            }
        }
    });
drag.start(e);
});
drawline();
}

/* Menu that is shown after end point has been dropped to element.
 * Used to choose which questions/courses must be completed before
 * advansing.
 */
function dropMenu(pDiv){
var menu = new Element('div', {
'styles' :{
        'position' : 'absolute',
        'text-align' : 'center',
        'border' : '2px solid black',
        'width' : 160,
        'background' : '#caffee',
        'z-index' : 5,
        'top' : pDiv.getPosition().y,
        'left' : pDiv.getPosition().x
            }

        });
var cancel = new Element('a', {
    'text': 'X',
    'title': 'Cancel',
    'href':'javascript:  ;',
    'styles' : {
            'color': '#FF0000',
            'position': 'absolute',
            'right' : 0,
            'text-decoration': 'none'
    },
    'events' : {'click' : function(){
                menu.destroy();
                }
    }
 });

menu.grab(cancel);
var tab = new Element('tbody');
menu.grab(new Element('table').grab(tab));

var parents = getParentBox(pDiv.id);
parents.each(function(id){
        var el = new Element('input', {
            'type': 'checkbox',
            'id': 'req_'+id,
            'name' : 'req_'+id,
            'value' : id
            });
    if(boxData.get(pDiv.id+'_required').contains(id)){
    el.set('checked','checked');
    }
        tab.grab(new Element('tr').adopt(new Element('td').grab(el),
            new Element('td').grab(new Element('label',{
                    'for' : 'req_' + id,
                    'text' : 'Require '+ boxData.get(id)
                    }))));
        });
var submit = new Element('input',{
        'type' : 'button',
        'value' : 'set',
        'events' : {'click': function(){
                var req = new Array();
                menu.getElements('input[name^=req]').each(function(chk){
                    if(chk.checked){
                        req.include(chk.value);
                    }
                    });
                boxData.set(pDiv.id+'_required',req);
                menu.destroy();
        }}
        });
menu.grab(new Element('hr'));
menu.grab(submit);
$(document.body).grab(menu);
}

/* Creates new box and sets child relations and end points*/
function newBox(to, value, description, type){
var pDiv = $(to);
lkm = boxData.get('lkm');
while($('b'+lkm)!==null){
    lkm++;
}
var id = 'b'+ lkm;
boxData.set('lkm', lkm);
boxData.set(id, value);
boxData.set(id+'_required', new Array());
if(boxData.get('endPoints').contains(pDiv.id) == true){
    boxData.get('endPoints').erase(pDiv.id);
    $('ep_'+pDiv.id).destroy();
}
    childBoxes.set('b'+lkm , new Array());

if(type == "after"){
childBoxes.set(id, childBoxes.get(pDiv.id));
childBoxes.set(pDiv.id, new Array());
getChildBox(id).each(function(id){
        if(boxData.get('endPoints').contains(id)){
            ep = $('ep_'+id);
            ep.setStyle('top', ep.getPosition().y + 75);
            }
        el = $(id);
        el.setStyle('top', el.getPosition().y + 75);
        });
}

cLkm = childBoxes.get(pDiv.id).length;

childBoxes.set(pDiv.id , childBoxes.get(pDiv.id).include(id));

if(/random|select/.test(type)){
boxData.set(pDiv.id+'_type',type);
}
if(type == "wrong"){
boxData.set(pDiv.id + '_wrong', id);
}
var box = new Element('div', {
    'id' : id,
    'class' : 'l3'
});
box.setStyles({
		'text-align' : 'center',
		'cursor' : 'move',
		'width' : '150px',
		'height' : '50px'
		});
box.height = 50;
box.widht = 150;
var content = document.createTextNode(description);
box.appendChild(content);
box.grab(new Element('br'));
color = '81BBF2';
/*
color = pDiv.id.length * 50000+ 150000;
color = color.toString(16);
while(color.length < 6){
color = '0' + color;
}
*/
box.style.background = '#' + color;
var but = new Element('input', {
        'type' : 'button',
        'value' : 'Edit'
        });
but.inject(box);
but.addEvent('click', function(){ editMenu(this);});
box.inject(document.body);
bX =  $(pDiv).getPosition().x + Math.ceil(cLkm/2) * 200 * Math.pow( -1, cLkm); 
bY =  $(pDiv).getPosition().y+75;
if(bX < 100){
bX = Math.abs(bX - 100)  + 100 ;
bY += 25;
}
box.setStyle('left', bX);
box.setStyle('top',bY);
var k = 0;
box.makeDraggable({
onDrag: function(){
        if(boxData.get('endPoints').contains(box.id)){
            $('ep_'+box.id).setStyles({
                'left': box.getPosition().x + box.getCoordinates().width /2 -10,
                'top': box.getPosition().y + 75
                });
        }
        drawline(box.id); 
        if(box.getPosition().x < 0){
            box.setStyle('left', 0);
        }
        if(box.getPosition().y < 0 ){
            box.setStyle('top', 0);
        }
    }
});

//window.scrollBy(0, 125);
if(type != "after"){
newEndPoint(box);
}
drawline();
}

/* Turns box tree into form with hidden inputs*/
function submitTree(){
var form = $('submitform');
if(!form.method){
var form = new Element('form',{
        'method' : 'post',
        'action':''
        });
}
childBoxes.each(function(value,id){
        childs = "";
        if(value){
        childs = value.toString();
        }
        if(id){
form.adopt(new Element('input', {
            'type':'hidden',
            'name': id+'[value]',
            'value' : boxData.get(id)
            }),
        new Element('input',{
            'type' : 'hidden',
            'name' : id+'[next]',
            'value' : childs
            }),
        new Element('input', {
            'type' : 'hidden',
            'name' : id+'[require]',
            'value' : boxData.get(id+'_required')
            }),
        new Element('input',{
            'type' : 'hidden',
            'name' : id+'[type]',
            'value' : boxData.get(id+'_type')
            }),
        new Element('input',{
            'type': 'hidden',
            'name': id+'[wrong]',
            'value' : boxData.get(id+'_wrong')
            })
    )}});

form.inject(document.body);
form.submit();
}

