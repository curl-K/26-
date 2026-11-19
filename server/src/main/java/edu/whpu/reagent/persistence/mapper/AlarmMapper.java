package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.Alarm;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.time.LocalDateTime;
import java.util.List;

@Mapper
public interface AlarmMapper extends BaseMapper<Alarm> {

    int insertAlarm(Alarm alarm);

    List<Alarm> listRecent();

    int acknowledge(@Param("id") long id, @Param("accountId") long accountId, @Param("at") LocalDateTime at);
}
