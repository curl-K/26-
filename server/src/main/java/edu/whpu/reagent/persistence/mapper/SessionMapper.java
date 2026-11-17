package edu.whpu.reagent.persistence.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import edu.whpu.reagent.domain.CabinetSession;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface SessionMapper extends BaseMapper<CabinetSession> {

    CabinetSession findActive(@Param("slot") int slot);

    int insertSession(CabinetSession session);

    int updateSession(CabinetSession session);
}
