package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.DeviceState;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;

@Mapper
public interface DeviceStateMapper extends BaseMapper<DeviceState> {

    int updateSeq(@Param("seq") int seq);

    int touchHeartbeat(@Param("at") LocalDateTime at);
}
