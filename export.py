import re
import addon_utils
import bpy
import time
import os
import argparse
import sys

scene = bpy.context.scene

class ArgumentParserForBlender(argparse.ArgumentParser):
    def _get_argv_after_doubledash(self):
        try: return sys.argv[sys.argv.index("--")+1:]
        except ValueError as e: return []
    def parse_args(self): return super().parse_args(args=self._get_argv_after_doubledash())

parser = ArgumentParserForBlender()

parser.add_argument("-q", "--quality", type=int, default=3, help="Quality render 32 * 2^q")
parser.add_argument("-s", "--start", type=int, default=bpy.context.scene.frame_start, help="Frame start")
parser.add_argument("-e", "--end", type=int, default= bpy.context.scene.frame_end,help="Frame end")
parser.add_argument("-rs", "--rangeSkip", type=int, default=1,help="Skip frames")

args = parser.parse_args()
quality = 16 * pow( 2, int( args.quality ) )

print( 'Render quality => ' + str( quality ) )

scene.cycles.device = 'GPU'
prefs = bpy.context.preferences
prefs.addons['cycles'].preferences.get_devices()
cprefs = prefs.addons['cycles'].preferences
print(bpy.data.objects.keys())

# Attempt to set GPU device types if available
for compute_device_type in ('CUDA', 'OPENCL', 'NONE'):
    try:
        cprefs.compute_device_type = compute_device_type
        break
    except TypeError:
        pass
#Enable all CPU and GPU devices
for device in cprefs.devices:
    if not re.match('intel', device.name, re.I):
        device.use = True
    else:
        device.use = False


#########################################
# Set vars
#########################################
start = args.start
end = args.end
scene.frame_set( start )
output_dir = bpy.path.abspath("//") + 'exports' +'_' + str( round( time.time() ) ) + '/'


#########################################
# Init
#########################################

meshArray = []
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH': 
        meshArray.append( obj.name )
        if 'Logo' in obj.name:
            bpy.context.view_layer.objects.active = obj
            bpy.context.object.hide_render = True

#########################################
# Renderer
#########################################
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.samples = quality
bpy.context.scene.render.tile_x = 256
bpy.context.scene.render.tile_y = 256
bpy.context.scene.cycles.use_denoising = True
bpy.context.scene.view_layers['View Layer'].cycles.use_denoising = True
bpy.context.scene.render.bake.margin = 16

def appendImageToMaterial( obj, image ):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set( True )
    bpy.context.view_layer.objects.active = obj
    
    for mat in obj.data.materials:
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        node = nodes.new('ShaderNodeTexImage')
        node.image = image
        node.location = (100,100)
        node.select = True
        nodes.active = node

#########################################
# Switch render settings
#########################################

def setRenderer( mode ):
    if mode == 'combined' :
        bpy.context.scene.cycles.bake_type = 'COMBINED'
        bpy.context.scene.render.bake.use_pass_direct = True
        bpy.context.scene.render.bake.use_pass_indirect = True
        bpy.context.scene.render.bake.use_pass_diffuse = True
        bpy.context.scene.render.bake.use_pass_glossy = False
        bpy.context.scene.render.bake.use_pass_transmission = False
        bpy.context.scene.render.bake.use_pass_ambient_occlusion = True
        bpy.context.scene.render.bake.use_pass_emit = False
    if mode == 'roughness' :
        bpy.context.scene.cycles.bake_type = 'ROUGHNESS'
    if mode == 'diffuse' :
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
    if mode == 'normal' :
        bpy.context.scene.cycles.bake_type = 'NORMAL'
    if mode == 'emission' :
        bpy.context.scene.cycles.bake_type = 'COMBINED'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = True
        bpy.context.scene.render.bake.use_pass_diffuse = True
        bpy.context.scene.render.bake.use_pass_glossy = False
        bpy.context.scene.render.bake.use_pass_transmission = False
        bpy.context.scene.render.bake.use_pass_ambient_occlusion = False
        bpy.context.scene.render.bake.use_pass_emit = False
    
    bpy.context.scene.cycles.use_denoising = True
    bpy.context.scene.view_layers['View Layer'].cycles.use_denoising = True
        
#########################################
# Geos bake SINGLE MAPS
#########################################

def bake_map( mapId ):
    
    setRenderer( mapId )
    for collection in bpy.data.collections:
        bpy.ops.object.select_all(action='DESELECT')
        if 'Letter_group' in collection.name:
            bpy.ops.image.new(name=collection.name+'_' + mapId, width=1024, height=1024)
            image = bpy.data.images[collection.name+'_' + mapId ]
            
            for mat in bpy.data.materials:
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                node = nodes.new('ShaderNodeTexImage')
                node.image = image
                node.location = (100,100)
                node.select = True
                nodes.active = node
            
            for obj in collection.all_objects:      
                if obj.type == 'MESH':
                    print( obj.name )
                    obj.select_set( True )
                    bpy.context.view_layer.objects.active = obj

        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
        image.filepath_raw = output_dir + collection.name + '_' + mapId + '.png'
        image.file_format = 'PNG'
        print( '------------------------------> _' + mapId + ' was saved' )
        image.save()

#########################################
# Plane bake
#########################################
def bake_plane():
    bakeDir = output_dir + 'plane_shadow/'
    os.makedirs( bakeDir )

    setRenderer( 'combined' )
    
    bpy.ops.object.select_all(action='DESELECT')
    matching = [s for s in meshArray if "Plane" in s ]
    plane = bpy.data.objects[ matching[ 0 ] ]
    bpy.ops.image.new(name='Plane_shadow', width=1024, height=1024)
    image = bpy.data.images['Plane_shadow']
    appendImageToMaterial( plane, image )
    bpy.context.active_object.data.uv_layers.active = bpy.context.active_object.data.uv_layers[0]
    plane.select_set( True )
    bpy.context.view_layer.objects.active = plane
    for frame in range(0,end,args.rangeSkip):
        scene.frame_set( frame )
        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
        image.filepath_raw = bakeDir + 'plane_shadow_' + str( frame ) + '.png'
        image.file_format = 'PNG'
        print( '------------------------------> Frame %s was saved to %s' % (str( frame ), image.filepath_raw ) )
        image.save()

def bake_plane_tiled():
    bakeDir = output_dir + 'plane_shadow_l/'
    os.makedirs( bakeDir )

    setRenderer( 'combined' )
    
    bpy.ops.object.select_all(action='DESELECT')
    matching = [s for s in meshArray if "Plane" in s ]
    plane = bpy.data.objects[ matching[ 0 ] ]
    bpy.ops.image.new(name='Plane_shadow', width=1024, height=1024)
    image = bpy.data.images['Plane_shadow']
    appendImageToMaterial( plane, image )
    
    plane.select_set( True )
    bpy.context.view_layer.objects.active = plane
    
    bpy.context.active_object.data.uv_layers.active = bpy.context.active_object.data.uv_layers[2]
    for frame in range(0,end,args.rangeSkip):
        scene.frame_set( frame )
        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
        image.filepath_raw = bakeDir + 'plane_shadow_' + str( frame ) + '.png'
        image.file_format = 'PNG'
        print( '------------------------------> Frame %s was saved to %s' % (str( frame ), image.filepath_raw ) )
        image.save()

    bakeDir = output_dir + 'plane_shadow_r/'
    os.makedirs( bakeDir )
    
    bpy.context.active_object.data.uv_layers.active = bpy.context.active_object.data.uv_layers[3]
    for frame in range(0,end,args.rangeSkip):
        scene.frame_set( frame )
        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
        image.filepath_raw = bakeDir + 'plane_shadow_' + str( frame ) + '.png'
        image.file_format = 'PNG'
        print( '------------------------------> Frame %s was saved to %s' % (str( frame ), image.filepath_raw ) )
        image.save()

#########################################
# Plane bake emissive
#########################################

def bake_emissive():
    setRenderer( 'emission' )
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 0
    
    bpy.context.scene.cycles.samples = 16 * pow( 2, int( args.quality - 1 ) )
    emiColors = [ (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1) ]
    emiColors2 = [ (0.05, 0, 0, 1), (0, 0.05, 0, 1), (0, 0, 0.05, 1) ]
    colIndex = 0
    for collection in bpy.data.collections:
        for c in bpy.data.collections:
            c.hide_render = True
        collection.hide_render = False
        if 'Letter_group' in collection.name:
            objindex = 0
            for obj in collection.all_objects:
                if obj.type == 'MESH':
                    for mat in obj.data.materials:
                        if "Letter" in mat.name:
                            om = mat
                            pm = mat
                            nm = mat.copy()
                            nm.name = om.name + '_emi_' + str( objindex )
                            nm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = emiColors[ objindex ]
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = nm
                        if "Inner" in mat.name:
                            om = mat
                            pmi = mat
                            nm = mat.copy()
                            nm.name = om.name + '_emi_' + str( objindex )
                            nm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = emiColors[ objindex ]
                            nm.node_tree.nodes["Principled BSDF"].inputs[17].default_value = emiColors2[ objindex ]
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = nm
                    objindex += 1
            # Colors swapped, do bake

            
            bakeDir = output_dir + collection.name + '_emission/'
            os.makedirs( bakeDir )
            bpy.ops.object.select_all(action='DESELECT')
            matching = [s for s in meshArray if "Plane" in s ]
            plane = bpy.data.objects[ matching[ 0 ] ]
            bpy.ops.image.new(name='Plane_emission_' + collection.name, width=512, height=512)
            image = bpy.data.images['Plane_emission_' + collection.name]
            appendImageToMaterial( plane, image )
            plane.select_set( True )
            bpy.context.view_layer.objects.active = plane
            bpy.context.active_object.data.uv_layers.active = bpy.context.active_object.data.uv_layers[1]
            
            for frame in range(0,end,args.rangeSkip):
                scene.frame_set( frame )
                bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
                image.filepath_raw = bakeDir + collection.name + '_emission_' + str( frame ) + '.png'
                image.file_format = 'PNG'
                print( '------------------------------> Frame %s for ' % ( str( frame ) ) + collection.name  + ' emission was saved to %s' % ( image.filepath_raw ) )
                image.save()

            # Restore color
            for obj in collection.all_objects:
                if obj.type == 'MESH':
                    for mat in obj.data.materials:
                        if "Letter" in mat.name:
                            om = mat
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = pm
                        if "Inner" in mat.name:
                            om = mat
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = pmi
            bpy.context.active_object.data.uv_layers.active = bpy.context.active_object.data.uv_layers[0]
        colIndex += 1
    bpy.context.scene.cycles.samples = quality
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[1].default_value = 0.5
                    

#########################################
# Geos bake shadow
#########################################
def bake_geos():
    setRenderer( 'combined' )
    
    for collection in bpy.data.collections:
        if 'Letter_group' in collection.name:
            bpy.ops.object.select_all(action='DESELECT')
            bakeDir = output_dir + collection.name + '_shadow/'
            os.makedirs( bakeDir )
            bpy.ops.image.new(name=collection.name, width=1024, height=1024, color=(1.0,1.0,1.0,1.0))
            image = bpy.data.images[collection.name]
            bpy.context.scene.render.bake.use_clear = False
            for mat in bpy.data.materials:
                if "Cap" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 1, 1, 1)
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                node = nodes.new('ShaderNodeTexImage')
                node.image = image
                node.location = (100,100)
                node.select = True
                nodes.active = node
            
            for frame in range(0,end,args.rangeSkip):
                scene.frame_set( frame )
                
                for obj in collection.all_objects:
                    bpy.ops.object.select_all(action='DESELECT')
                    if obj.type == 'MESH':
                        obj.select_set( True )
                        bpy.context.view_layer.objects.active = obj
                        bpy. ops.object.bake(type=bpy.context.scene.cycles.bake_type)
                    image.filepath_raw = bakeDir + collection.name + '_shadow_' + str( frame ) + '.png'
                    
                    image.file_format = 'PNG'
                    image.save()
            for mat in bpy.data.materials:
                if "Cap" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ( 0.016, 0.016, 0.016, 1)

def bake_mapid(): 
    setRenderer( 'diffuse' )
    for collection in bpy.data.collections:
        if 'Letter_group' in collection.name:
            bpy.ops.object.select_all(action='DESELECT')
            bakeDir = output_dir
            bpy.ops.image.new(name=collection.name, width=1024, height=1024)
            image = bpy.data.images[collection.name]
            bpy.context.scene.render.bake.use_clear = False

            for mat in bpy.data.materials:
                if "Cap" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0, 0, 1)
                if "Letter" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0, 1, 0, 1)
                if "Inner" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0, 0, 1, 1)
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                node = nodes.new('ShaderNodeTexImage')
                node.image = image
                node.location = (100,100)
                node.select = True
                nodes.active = node
            
            
            for obj in collection.all_objects:
                bpy.ops.object.select_all(action='DESELECT')
                if obj.type == 'MESH':
                    obj.select_set( True )
                    bpy.context.view_layer.objects.active = obj
                    bpy. ops.object.bake(type=bpy.context.scene.cycles.bake_type)
                image.filepath_raw = bakeDir + collection.name + '_mapid.png'
                image.file_format = 'PNG'
                image.save()
            for mat in bpy.data.materials:
                if "Cap" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ( 0.016, 0.016, 0.016, 1)
                if "Letter" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 1, 1, 1)
                if "Inner" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 1, 1, 1)

yes = {'yes','y', 'ye'}
no = {'no','n',''}
bake_maps = []

if input('Bake all maps? [y/N]').lower() in yes: bake_maps.append('all')
else :
    # if input('Bake Roughness? [y/N]').lower() in yes: bake_maps.append('roughness')
    # if input('Bake Normal? [y/N]').lower() in yes: bake_maps.append('normal')
    # if input('Bake Diffuse? [y/N]').lower() in yes: bake_maps.append('diffuse')
    if input('Bake geos mat ids? [y/N]').lower() in yes: bake_maps.append('mapid')
    if input('Bake Plane shadow? [y/N]').lower() in yes: bake_maps.append('plane')
    if input('Bake Geos shadow? [y/N]').lower() in yes: bake_maps.append('geos')
    if input('Bake Geos emissive? [y/N]').lower() in yes: bake_maps.append('emissive')
    if input('Bake Plane Tiled? [y/N]').lower() in yes: bake_maps.append('bakeTiled')

    

if len(bake_maps) == 0 : 
    print('No maps selected to bake')
else:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    print( 'Exporting to ' + output_dir )
    # if "roughness" in bake_maps or "all" in bake_maps: bake_map('roughness')
    # if "normal" in bake_maps or "all" in bake_maps: bake_map('normal')
    # if "diffuse" in bake_maps or "all" in bake_maps: bake_map('diffuse')
    if "mapid" in bake_maps or "all" in bake_maps: bake_mapid()
    if "plane" in bake_maps or "all" in bake_maps: bake_plane()
    if "geos" in bake_maps or "all" in bake_maps: bake_geos()
    if "emissive" in bake_maps or "all" in bake_maps: bake_emissive()
    if "bakeTiled" in bake_maps or "all" in bake_maps: bake_plane_tiled()

# bpy.ops.wm.save_as_mainfile(filepath=output_dir+'demo.blend')

bpy.ops.wm.quit_blender()
