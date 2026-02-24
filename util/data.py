BASE_OBJ = ['lamp', 'armset', 'backrest', 'bathtub', 'bed', 'cabinet_door', 'door', 'drawer', 
             'garbage', 'microwave', 'mirror', 'pillow', 'refrigerator', 'screen', 'sink', 'seat', 
             'stairway', 'table', 'window']  # 修改为平面列表，确保len(BASE_OBJ)=19，匹配Seen数据集的对象数量
NOVEL_OBJ = [ ]
SEEN_AFF = ['light', 'swing_open', 'lie', 'sit', 'rest_arm', 'lean_back', 'climb', 
            'wash', 'drop', 'display', 'lying_on', 'bathe', 'place', 'look_through', 'reflect_image',
            'open', 'heating', 'pull', 'refrigerate']
UNSEEN_AFF = [ ]