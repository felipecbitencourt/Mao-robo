"""Split an OBJ file into separate OBJ files per `o <name>` object.

This script keeps all vertex/texcoord/normal declarations in each output file (simple duplication)
so face indices remain valid without re-indexing.

Usage:
    python tools/split_obj_by_object.py "path/to/Rigged Hand.obj"

Outputs files next to the input file named:
    <origbasename>_<objectname>.obj

"""
import sys
import os
import io


def sanitize_name(name: str) -> str:
    return "".join(c if c.isalnum() or c in (' ', '-', '_', '.') else '_' for c in name).replace(' ', '_')


def split_obj_by_object(input_path: str):
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as fh:
        lines = fh.readlines()

    header_lines = []
    v_lines = []
    vt_lines = []
    vn_lines = []
    other_pre = []

    objects = []  # list of (name, lines)
    current_obj = None
    current_lines = []

    for ln in lines:
        if ln.startswith('v '):
            v_lines.append(ln)
            continue
        if ln.startswith('vt '):
            vt_lines.append(ln)
            continue
        if ln.startswith('vn '):
            vn_lines.append(ln)
            continue
        if ln.startswith('o '):
            # start new object
            if current_obj is not None:
                objects.append((current_obj, current_lines))
            current_obj = ln.strip()[2:]
            current_lines = [ln]
            continue
        # keep mtllib and comments in header
        if current_obj is None:
            if ln.startswith('mtllib') or ln.startswith('#') or ln.startswith('g ') or ln.startswith('usemtl'):
                header_lines.append(ln)
            else:
                other_pre.append(ln)
            continue
        # inside object section
        current_lines.append(ln)

    if current_obj is not None:
        objects.append((current_obj, current_lines))

    if not objects:
        print('No objects ("o ") found in OBJ file. Nothing to split.')
        return

    base_dir = os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    for objname, obj_lines in objects:
        safe = sanitize_name(objname)
        out_name = f"{base_name}_{safe}.obj"
        out_path = os.path.join(base_dir, out_name)
        with open(out_path, 'w', encoding='utf-8') as out:
            # write header
            for h in header_lines:
                out.write(h)
            # ensure mtllib preserved: if not present, leave as-is
            # write vertices
            for v in v_lines:
                out.write(v)
            for vt in vt_lines:
                out.write(vt)
            for vn in vn_lines:
                out.write(vn)
            # write the object block
            out.writelines(obj_lines)
        print('Wrote', out_path)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python tools/split_obj_by_object.py path/to/file.obj')
        sys.exit(1)
    split_obj_by_object(sys.argv[1])
