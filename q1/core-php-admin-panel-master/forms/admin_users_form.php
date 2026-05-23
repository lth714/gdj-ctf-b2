<fieldset>
    <!-- Form Name -->
    <legend><?php echo ($edit) ? '编辑用户' : '添加用户'; ?></legend>
    <!-- Text input-->
    <div class="form-group">
        <label class="col-md-4 control-label">用户名</label>
        <div class="col-md-4 inputGroupContainer">
            <div class="input-group">
                <span class="input-group-addon"><i class="glyphicon glyphicon-user"></i></span>
                <input  type="text" name="username" autocomplete="off" placeholder="用户名" class="form-control" value="<?php echo ($edit) ? $user['username'] : ''; ?>" autocomplete="off">
            </div>
        </div>
    </div>
    <!-- Text input-->
    <div class="form-group">
        <label class="col-md-4 control-label" >密码<?php echo ($edit) ? '' : ''; ?></label>
        <div class="col-md-4 inputGroupContainer">
            <div class="input-group">
                <span class="input-group-addon"><i class="glyphicon glyphicon-lock"></i></span>
                <input type="password" name="password" autocomplete="off" placeholder="<?php echo ($edit) ? '留空则不修改' : '密码'; ?>" class="form-control" <?php echo ($edit) ? '' : 'required=""'; ?> autocomplete="off">
            </div>
        </div>
    </div>
    <!-- Text input-->
    <div class="form-group">
        <label class="col-md-4 control-label">昵称</label>
        <div class="col-md-4 inputGroupContainer">
            <div class="input-group">
                <span class="input-group-addon"><i class="glyphicon glyphicon-tag"></i></span>
                <input type="text" name="nickname" autocomplete="off" placeholder="昵称" class="form-control" value="<?php echo ($edit) ? $user['nickname'] : ''; ?>">
            </div>
        </div>
    </div>
    <!-- Text input-->
    <div class="form-group">
        <label class="col-md-4 control-label">邮箱</label>
        <div class="col-md-4 inputGroupContainer">
            <div class="input-group">
                <span class="input-group-addon"><i class="glyphicon glyphicon-envelope"></i></span>
                <input type="email" name="email" autocomplete="off" placeholder="邮箱" class="form-control" value="<?php echo ($edit) ? $user['email'] : ''; ?>">
            </div>
        </div>
    </div>
    <!-- radio checks -->
    <div class="form-group">
        <label class="col-md-4 control-label">角色</label>
        <div class="col-md-4">
            <div class="radio">
                <label>
                    <input type="radio" name="role" value="admin" required="" <?php echo ($edit && $user['role'] =='admin') ? "checked": "" ; ?>/> 系统管理员
                </label>
            </div>
            <div class="radio">
                <label>
                    <input type="radio" name="role" value="operator" required="" <?php echo ($edit && $user['role'] =='operator') ? "checked": "" ; ?>/> 运营人员
                </label>
            </div>
            <div class="radio">
                <label>
                    <input type="radio" name="role" value="editor" required="" <?php echo ($edit && $user['role'] =='editor') ? "checked": "" ; ?>/> 编辑人员
                </label>
            </div>
        </div>
    </div>
    <!-- radio checks -->
    <div class="form-group">
        <label class="col-md-4 control-label">状态</label>
        <div class="col-md-4">
            <div class="radio">
                <label>
                    <input type="radio" name="status" value="1" required="" <?php echo ($edit && $user['status'] =='1') ? "checked": ((!$edit) ? "checked" : ""); ?>/> 启用
                </label>
            </div>
            <div class="radio">
                <label>
                    <input type="radio" name="status" value="0" required="" <?php echo ($edit && $user['status'] =='0') ? "checked": "" ; ?>/> 禁用
                </label>
            </div>
        </div>
    </div>
    <!-- Button -->
    <div class="form-group">
        <label class="col-md-4 control-label"></label>
        <div class="col-md-4">
            <button type="submit" class="btn btn-warning" >保存 <span class="glyphicon glyphicon-send"></span></button>
        </div>
    </div>
</fieldset>