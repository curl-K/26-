package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.AccessRecord;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface AccessMapper extends BaseMapper<AccessRecord> {

    int insertAccess(AccessRecord record);

    List<AccessRecord> listBySession(@Param("sessionId") long sessionId);

    int removeById(@Param("id") long id);
}
